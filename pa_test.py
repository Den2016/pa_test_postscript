import math
import re
import os
import sys
import argparse
import logging


# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Configure logging to save in the script's directory
log_file_path = os.path.join(script_dir, "pa_test_log.txt")
logging.basicConfig(
    filename=log_file_path,
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

class Extruder(object):

    nozzle_diameter = 0.4
    extrusion_width = 0.42
    layer_height = 0.2
    use_firmware_retraction = 0
    retract_length = 0.8
    retract_speed = 0.8

    def __init__(self):
        pass
    
    def calcExtrusionOnLengthByCoords(self,start_x,start_y,end_x,end_y):
        length = math.sqrt(math.pow(abs(end_x-start_x),2)+math.pow(abs(end_y-start_y),2))*self.extrusion_width*self.layer_height*self.nozzle_diameter
        length = f"{length:.5f}"
        while(len(length)>0 and length[0] == '0'):
            length=length[1:]
        return length

    def retract(self):
        if(self.use_firmware_retraction == 1):
            return "G10 ; retract\n"
        else:
            s = str(self.retract_length)
            while(len(s)>0 and s[0] == '0'):
                s=s[1:]
            return f"G1 E-{s} F{self.retract_speed*60:.0f}  ; retract\n"    
        
    def unretract(self):
        if(self.use_firmware_retraction == 1):
            return "G11 ; unrectract\n"
        else:
            s = str(self.retract_length)
            while(len(s)>0 and s[0] == '0'):
                s=s[1:]
            return f"G1 E{s} F{self.retract_speed*60:.0f}  ; unretract\n"
        
class GCodeAnalyze:
    file_input = ""

    startPA = 0.13
    stepPA = 0.005
    endPA = 0

    #gcode params
    retract_length = 0.8 
    retract_speed = 30
    nozzle_diameter = 0.4
    use_firmware_retraction = 0
    external_perimeter_speed = 60
    travel_speed = 150
    external_perimeter_extrusion_width = 0.42
    gcode_comments = 0
    gcode_label_objects = ""
    use_relative_e_distances = 0
    top_one_wall_type = ""
    filament_type = ""
    temperature = 0
    lastInfillZ = ""
    infillLayers = []


    steps = []
    sizes = dict()
    layers = dict()
    instances = 0

    def __init__(self):
        pass

    def calcStep(self,start_pa,end_pa):
        try:
            start_pa=float(start_pa)
            end_pa=float(end_pa)
            step = float(f'{(end_pa-start_pa)/self.instances:.3f}')
            self.startPA=start_pa
            self.stepPA=step
            idx=self.instances
            self.steps = []
            pa=self.startPA
            while idx != 0:
                self.steps.append(pa)
                pa=round((pa+self.stepPA)*1000)/1000
                idx=idx-1
                self.endPA = pa
        except:
            pass

    def analyzeFile(self):
        #logging.info(f"analyzeFile: "{self.file_input});
        maxval = 0
        self.steps = []
        self.dict = ()
        self.layers = ()
        sizes = dict()
        currentZ = ";Z:0"
        infill = False
        self.infillLayers = []
        with open(self.file_input) as file:											# Открытие файла с g-кодом
            instance = -1
            for line in file:
                # проверяем на объект
                if ('EXCLUDE_OBJECT_START' in line):
                    instance = int(re.findall(r'\d+', line)[0])
                    if(instance>maxval):
                        maxval=instance
                    if(instance not in self.sizes):
                        self.sizes[instance]=[-1,-1,-1,-1]
                if ('EXCLUDE_OBJECT_END' in line):
                    instance = -1

                if line.startswith((";Z:")):
                    if(infill):
                       self.infillLayers.append(self.currentZ)
                       self.lastInfillZ = self.currentZ
                       infill = False
                    self.currentZ=line

                if line.endswith(("; infill\n")):
                    infill = True

                if("; nozzle_diameter = " in line):
                    self.nozzle_diameter = float(line.split()[-1])

                if("; use_firmware_retraction " in line):
                    self.use_firmware_retraction = int(line.split()[-1])

                if("; gcode_comments " in line):
                    self.gcode_comments = int(line.split()[-1])

                if("; use_relative_e_distances " in line):
                    self.use_relative_e_distances = int(line.split()[-1])

                if("; gcode_label_objects " in line):
                    self.gcode_label_objects = line.split()[-1]

                if("; top_one_wall_type " in line):
                    self.top_one_wall_type = line.split()[-1]

                if("; filament_type " in line):
                    self.filament_type = line.split()[-1]

                if("; temperature " in line):
                    self.temperature = int(line.split()[-1])

                if("; retract_length " in line):
                    self.retract_length = float(line.split()[-1])

                if("; external_perimeter_speed " in line):
                    self.external_perimeter_speed = float(line.split()[-1])

                if("; travel_speed " in line):
                    self.travel_speed = float(line.split()[-1])

                if("; retract_speed " in line):
                    self.retract_speed = float(line.split()[-1])

                if("; external_perimeter_extrusion_width " in line):
                    self.external_perimeter_extrusion_width = float(line.split()[-1])


                if(instance != -1):
                    if('perimeter' in line and "G1 " in line and "E" in line):
                        point_x = line[line.find("X")+1:line.find(";")]				# Получаем часть строки от символа X до точки с запятой
                        point_x = float(point_x.split(' ')[0])							# Разбиваем строку. Разделитель " ". Первый элемент - координата X.
                        if(self.sizes[instance][0] == -1):    self.sizes[instance][0] = point_x
                        if(self.sizes[instance][0]>point_x):  self.sizes[instance][0] = point_x
                        if(self.sizes[instance][2] == -1):    self.sizes[instance][2] = point_x
                        if(self.sizes[instance][2]<point_x):  self.sizes[instance][2] = point_x
                            
                        point_y = line[line.find("Y")+1:line.find(";")]				# Получаем часть строки от символа X до точки с запятой
                        point_y = float(point_y.split(' ')[0])							# Разбиваем строку. Разделитель " ". Первый элемент - координата X.
                        if(self.sizes[instance][1] == -1):    self.sizes[instance][1] = point_y
                        if(self.sizes[instance][1]>point_y):  self.sizes[instance][1] = point_y
                        if(self.sizes[instance][3] == -1):    self.sizes[instance][3] = point_y
                        if(self.sizes[instance][3]<point_y):  self.sizes[instance][3] = point_y


            #отсортируем кубики
            sizes = sorted(self.sizes.values(),key=lambda size:(size[1],size[2]))
            self.sizes = dict()
            for n,step in enumerate(sizes):
                self.sizes[n+1]=step


            idx=maxval
            pa=self.startPA
            while idx != 0:
                self.steps.append(pa)
                pa=round((pa+self.stepPA)*1000)/1000
                idx=idx-1
        self.instances = len(self.steps)
        self.calcStep(self.startPA,self.instances*self.stepPA)
        pass

    def askParams(self):
        print(f"\nПараметры по умолчанию:\nСтартовый PA: {self.startPA}\nКонечный PA{self.endPA}\nШаг изменения PA: {self.stepPA}")
        try:
            params = int(input("Использовать параметры по умолчанию? Да - 1, нет - 0 [1]: "))
        except:
            params = 1
        if(params == 0):
            while True:
                while True:
                    try:
                        pa = input(f"Введите стартовый PA [{self.startPA}]: ")
                        if pa=="":
                            break
                        self.startPA=float(pa)
                        break
                    except:
                        print("Неверный формат числа с плавающей точкой, введите еще раз")
                        pass
                while True:
                    try:
                        pa = float(input(f"Введите конечный PA [{self.endPA}]: "))
                        if pa=="":
                            break
                        self.endPA = float(pa)
                        break
                    except:
                        print("Неверный формат числа с плавающей точкой, введите еще раз")
                        pass
                self.calcStep(self.startPA,self.endPA)
                print("\nВыбранные параметры")
                print(f"Стартовый PA: {self.startPA}")
                print(f"Конечный PA: {self.endPA}")
                print(f"Расчетные значения PA: {self.steps}")
                try:
                    params = int(input("Принять эти параметры и продолжить (если нет, то повторный ввод)? Да - 1, нет - 0 [1]: "))
                except:
                    params = 1
                if params == 1:
                    break
                
#        pa = self.startPA
#        for n,step in enumerate(self.steps):
#            self.steps[n]=pa
#            pa=round((pa+self.stepPA)*1000)/1000
#        print(f"Steps {self.steps}")    

    def checkConditions(self, doNotRaise = False):
        problems = ""
        if(self.gcode_comments == 0):
            problems = problems + 'Поставьте галочку "Подробный G-код" в профиле печати в разделе выходные параметры \n'
        if(self.gcode_label_objects != "firmware"):
            problems = problems + 'Параметр "Название моделей" в профиле печати в разделе выходные параметры установите в значение "Зависит от прошивки"\n'
        if(self.use_relative_e_distances == 0):
            problems = problems + 'В профиле принтера в разделе "Дополнительно" установите галочку "Использовать относительные координаты для экструдера(Е)"\n'
        if(len(problems)>0):
            if doNotRaise:
                return problems
            else:
                print("Для корректной работы скрипта необходимо выполнить следующие условия")
                print(problems)
                logging.info(f"Problems: {problems}")
                raise SystemExit(code=3)
        return problems

class GCodeChange(object):

    x0 = 0.0
    xmax = 2.5
    y0 = 0.0
    ymax = 5.0
    offset_x = 3.2
    offset_y = 5
    output_filename = ""

    digits = {
        '0':[[x0,ymax,1],[xmax,ymax,1],[xmax,y0,1],[x0,y0,1],[xmax+1,y0,0]],
        '1':[[xmax*.4,y0,0],[xmax*.4,ymax,1],[xmax+1,y0,0]],
        '2':[[xmax,y0,0],[x0,y0,1],[x0,ymax/2,1],[xmax,ymax/2,1],[xmax,ymax,1],[x0,ymax,1],[xmax+1,y0,0]],
        '3':[[xmax,y0,1],[xmax,ymax/2,1],[x0,ymax/2,0],[xmax,ymax/2,1],[xmax,ymax,1],[x0,ymax,1],[xmax+1,y0,0]],
        '4':[[xmax,y0,0],[xmax,ymax,1],[xmax,ymax/2,0],[x0,ymax/2,1],[x0,ymax,1],[xmax+1,y0,0]],
        '5':[[xmax,y0,1],[xmax,ymax/2,1],[x0,ymax/2,1],[x0,ymax,1],[xmax,ymax,1],[xmax+1,y0,0]],
        '6':[[xmax,ymax,0],[x0,ymax,1],[x0,y0,1],[xmax,y0,1],[xmax,ymax/2,1],[x0,ymax/2,1],[xmax+1,y0,0]],
        '7':[[xmax,y0,0],[xmax,ymax,1],[x0,ymax,1],[xmax+1,y0,0]],
        '8':[[x0,ymax,1],[xmax,ymax,1],[xmax,y0,1],[x0,y0,1],[x0,ymax/2,0],[xmax,ymax/2,1],[xmax+1,y0,0]],
        '9':[[xmax,y0,1],[xmax,ymax,1],[x0,ymax,1],[x0,ymax/2,1],[xmax,ymax/2,1],[xmax+1,y0,0]],
        '.':[[xmax/2-0.3,y0,0],[xmax/2-0.3,y0+0.3,1],[xmax/2,y0+0.3,1],[xmax/2,y0,1],[xmax+0.8,y0,0]],
        ',':[[xmax/2-0.3,y0,0],[xmax/2-0.3,y0+0.3,1],[xmax/2,y0+0.3,1],[xmax/2,y0,1],[xmax+0.8,y0,0]]
    }

    def Change(self,GcA:GCodeAnalyze, Extruder:Extruder):
        self.output_filename=f"{GcA.file_input}_tmp"
        tmp = open(self.output_filename,"w")	
        Extruder.nozzle_diameter = GcA.nozzle_diameter
        Extruder.use_firmware_retraction = GcA.use_firmware_retraction
        Extruder.retract_length = GcA.retract_length
        Extruder.retract_speed = GcA.retract_speed


        # начинаем формирование модифицированного файла
        digitsWrited = False
        waitNoInfillLayer = True

        with open(GcA.file_input) as file:											# Открытие файла с g-кодом
            waitDigitLayer = True # ждем слоя, на котором будем рисовать цифры
            for line in file:
                tmp.write(line)			
                if ('EXCLUDE_OBJECT_START' in line):
        #			numbers = int(''.join(c if c.isdigit() else ' ' for c in line).split())
                    instance = int(re.findall(r'\d+', line)[0])
                    tmp.write("M900 K"+str(GcA.steps[instance-1])+"\n")
                if( line.startswith(";Z:") and (line not in GcA.infillLayers)):
                    # слой, на котором надо нарисовать цифры
                    waitNoInfillLayer = False # дождались слоя )) 
                if(not waitNoInfillLayer and 'EXCLUDE_OBJECT_END' in line and not digitsWrited):
                    # дождались нужного слоя и нужного места, сейчас будем вставлять код, который рисует цифры
                    for idx,step in enumerate(GcA.steps):
                        box = idx+1
                        size = GcA.sizes[box] # получили координаты квадрата, далее надо определить начальную точку
                        start_x = float(size[0])+self.offset_x
                        start_y = float(size[1])+self.offset_y
                        old_x = start_x
                        old_y = start_y
                        delta_x = 0
                        tmp.write(f"G1 X{start_x:.5f} Y{start_y:.5f} F{GcA.travel_speed*60:.0f}; number start point\n")
                        #unretract
                        tmp.write(Extruder.unretract())
                        retracted = False
                        for c in str(step):
                            digit = self.digits[c]
                            tmp.write(f"G1 F{GcA.external_perimeter_speed*60:.0f}\n")
                            for coords in digit:
                                #пробегаем по координатам цифры и рисуем
                                point_x = start_x+delta_x+coords[0]
                                point_y = start_y+coords[1]
                                if(coords[2] == 1):
        #							lE = math.sqrt(math.pow(abs(point_x-old_x),2)+math.pow(abs(point_y-old_y),2))*constE
                                    lE = Extruder.calcExtrusionOnLengthByCoords(old_x,old_y,point_x,point_y)
                                    if(retracted):
                                        #unretract
                                        tmp.write(Extruder.unretract())
                                        retracted = False

                                    tmp.write(f"G1 X{point_x:.4f} Y{point_y:.4f} E{lE} \n")
                                else:
                                    #retract
                                    if(not retracted): tmp.write(Extruder.retract())
                                    retracted = True
                                    tmp.write(f"G1 X{point_x:.5f} Y{point_y:.5f} F{GcA.travel_speed*60:.0f}\n")

                                old_x=point_x
                                old_y=point_y
                            delta_x=point_x-start_x
                    digitsWrited = True
                    tmp.write("G92 E0\n")
        tmp.close()
        file.close()
        os.remove(GcA.file_input)
        os.rename(self.output_filename, GcA.file_input)


        pass

def remove_pp_extension(filename):
    if filename.endswith('.pp'):
        return filename[:-3]  # Убираем последние 3 символа '.pp'
    return filename

# Main execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post-process G-code for best PA value.")
    parser.add_argument("input_file", help="Path to the input G-code file")
    parser.add_argument("-startPA", type=float, default=0.05, help="Start PA value (default: 0.05)")
    parser.add_argument("-endPA", type=float, default=0.15, help="End PA value (default: 0.15)")
    args = parser.parse_args()

    input_file = remove_pp_extension(args.input_file)
    logging.info("Starting G-code processing")
    logging.info(f"Input file: {input_file}")
    logging.info(f"Start PA: {args.startPA}")
    logging.info(f"End PA: {args.endPA}")

    for i, arg in enumerate(sys.argv):
        logging.info(f"Аргумент {i}: {arg}")

    GcA = GCodeAnalyze()
    Extruder = Extruder()
    GcA.file_input = input_file
    GcA.analyzeFile()
    GcA.checkConditions()
    GcA.calcStep(args.startPA,args.endPA)
    GcC = GCodeChange()
    GcC.Change(GcA,Extruder)


