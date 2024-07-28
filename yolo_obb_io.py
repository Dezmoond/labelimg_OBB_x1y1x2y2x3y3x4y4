#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
import os
import math
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs
from libs.constants import DEFAULT_ENCODING

TXT_EXT = '.txt'
ENCODE_METHOD = 'utf-8'

class YOLOOBBWriter:
    def __init__(self, foldername, filename, imgSize, databaseSrc='Unknown', localImgPath=None):
        self.foldername = foldername
        self.filename = filename
        self.databaseSrc = databaseSrc
        self.imgSize = imgSize
        self.boxlist = []
        self.localImgPath = localImgPath
        self.verified = False

    def addBndBox(self, centre_x, centre_y, height, width, angle, name, difficult):
        bndbox = {'centre_x': centre_x, 'centre_y': centre_y, 'height': height, 'width': width, 'angle': angle}
        bndbox['name'] = name
        bndbox['difficult'] = difficult
        self.boxlist.append(bndbox)

    def save(self, classList=[], targetFile=None):
        img_height, img_width, img_z = self.imgSize  # Размеры изображения в пикселях

        out_file = None  # Обновляем yolo .txt
        out_class_file = None  # Обновляем class list .txt

        if targetFile is None:
            out_file = open(self.filename + TXT_EXT, 'w', encoding=ENCODE_METHOD)
            classesFile = os.path.join(os.path.dirname(os.path.abspath(self.filename)), "classes.txt")
            out_class_file = open(classesFile, 'w')

        else:
            out_file = codecs.open(targetFile, 'w', encoding=ENCODE_METHOD)
            classesFile = os.path.join(os.path.dirname(os.path.abspath(targetFile)), "classes.txt")
            out_class_file = open(classesFile, 'w')

        out_file.write("")
        first_line = True
        for box in self.boxlist:
            boxName = box['name']
            if boxName not in classList:
                classList.append(boxName)
            classIndex = classList.index(boxName)

            # Конвертируем координаты в формат YOLO OBB
            corners = self.convert_to_yolo_obb_corners(
                box['centre_x'], box['centre_y'],
                box['width'], box['height'],
                box['angle'], img_width, img_height
            )
            print(img_width, img_height)
            print("lj", corners)
            # Разделяем денормализованные координаты на два списка: x и y
            x_coords, y_coords = zip(*corners)
            # Повторно нормализуем
            corners = [(x / img_width, y / img_height) for x, y in zip(x_coords, y_coords)]
            print('после',corners)
            # Формируем строку для записи
            line = "%d %.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f" % (
                classIndex,
                corners[0][0], corners[0][1],
                corners[1][0], corners[1][1],
                corners[2][0], corners[2][1],
                corners[3][0], corners[3][1]
            )

        # Добавляем перенос строки перед всеми строками, кроме первой
            if not first_line:
                out_file.write("\n")
            else:
                first_line = False

            out_file.write(line)

        for c in classList:
            out_class_file.write(c + '\n')

        out_class_file.close()
        out_file.close()

    def convert_to_yolo_obb_corners(self, centre_x, centre_y, width, height, angle, img_width, img_height):
        # Добавляем 90 градусов к текущему углу
        angle += 90
        angle = -angle
        angle_rad = math.radians(angle)
        print(angle_rad)
        
        # Преобразование координат центра в пиксели
        cx = centre_x
        cy = centre_y
        w = width
        h = height
    
        # Определение координат углов прямоугольника до поворота
        corners = [
            (cx + w/2, cy + h/2),  # Top-right
            (cx - w/2, cy + h/2),  # Top-left
            (cx - w/2, cy - h/2),  # Bottom-left
            (cx + w/2, cy - h/2)   # Bottom-right
        ]
    
        # Поворот углов
        rotated_corners = []
        for x, y in corners:
            new_x = cx + (x - cx) * math.cos(angle_rad) - (y - cy) * math.sin(angle_rad)
            new_y = cy + (x - cx) * math.sin(angle_rad) + (y - cy) * math.cos(angle_rad)
            rotated_corners.append((new_x, new_y))
        
        return rotated_corners



class YoloOBBReader:

    def __init__(self, filepath, image, classListPath=None):
        self.shapes = []
        self.filepath = filepath

        if classListPath is None:
            dir_path = os.path.dirname(os.path.realpath(self.filepath))
            self.classListPath = os.path.join(dir_path, "classes.txt")
        else:
            self.classListPath = classListPath

        with open(self.classListPath, 'r') as classesFile:
            self.classes = classesFile.read().strip().split('\n')

        imgSize = [image.height(), image.width(), 1 if image.isGrayscale() else 3]
        self.imgSize = imgSize

        self.verified = False
        self.parseYoloOBBFormat()

    def getShapes(self):
        return self.shapes

    def addShape(self, label, centre_x, centre_y, height, width, angle, difficult):
        self.shapes.append((label, float(centre_x), float(centre_y), float(height), float(width), float(angle), None, None, difficult))

    def parseYoloOBBFormat(self):
        with open(self.filepath, 'r') as bndBoxFile:
            header = bndBoxFile.readline().strip()
            if header != "YOLO_OBB":
                raise ValueError("File format not recognized. Expected header 'YOLO_OBB'.")

            for bndBox in bndBoxFile:
                parts = bndBox.strip().split()
                
                # Debug output to identify issues
                if len(parts) != 6:
                    print(f"Warning: Unexpected format in line: {bndBox.strip()}. Expected 6 values but got {len(parts)}")
                    continue

                try:
                    classIndex = int(parts[0])
                    centre_x = float(parts[1])
                    centre_y = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])
                    angle = float(parts[5])
                    
                    label = self.classes[classIndex]
                    
                    self.addShape(label, centre_x, centre_y, height, width, angle, False)
                except ValueError as e:
                    print(f"Error parsing line: {bndBox.strip()}. {e}")