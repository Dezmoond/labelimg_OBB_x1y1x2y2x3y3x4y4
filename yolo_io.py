#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
import os
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs
from libs.constants import DEFAULT_ENCODING

TXT_EXT = '.txt'
ENCODE_METHOD = DEFAULT_ENCODING

class YOLOWriter:

    def __init__(self, foldername, filename, imgSize, databaseSrc='Unknown', localImgPath=None):
        self.foldername = foldername
        self.filename = filename
        self.databaseSrc = databaseSrc
        self.imgSize = imgSize
        self.boxlist = []
        self.localImgPath = localImgPath
        self.verified = False

    def addBndBox(self, xmin, ymin, xmax, ymax, name, difficult):
        bndbox = {'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax}
        bndbox['name'] = name
        bndbox['difficult'] = difficult
        self.boxlist.append(bndbox)

    def BndBox2YoloLine(self, box, classList=[]):
        xmin = box['xmin']
        xmax = box['xmax']
        ymin = box['ymin']
        ymax = box['ymax']

        xcen = float((xmin + xmax)) / 2 / self.imgSize[1]
        ycen = float((ymin + ymax)) / 2 / self.imgSize[0]

        w = float((xmax - xmin)) / self.imgSize[1]
        h = float((ymax - ymin)) / self.imgSize[0]

        # PR387
        boxName = box['name']
        if boxName not in classList:
            classList.append(boxName)

        classIndex = classList.index(boxName)

        return classIndex, xcen, ycen, w, h

    def save(self, classList=[], targetFile=None):

        out_file = None #Update yolo .txt
        out_class_file = None   #Update class list .txt

        if targetFile is None:
            out_file = open(
            self.filename + TXT_EXT, 'w', encoding=ENCODE_METHOD)
            classesFile = os.path.join(os.path.dirname(os.path.abspath(self.filename)), "classes.txt")
            out_class_file = open(classesFile, 'w')

        else:
            out_file = codecs.open(targetFile, 'w', encoding=ENCODE_METHOD)
            classesFile = os.path.join(os.path.dirname(os.path.abspath(targetFile)), "classes.txt")
            out_class_file = open(classesFile, 'w')


        for box in self.boxlist:
            classIndex, xcen, ycen, w, h = self.BndBox2YoloLine(box, classList)
            # print (classIndex, xcen, ycen, w, h)
            out_file.write("%d %.6f %.6f %.6f %.6f\n" % (classIndex, xcen, ycen, w, h))

        # print (classList)
        # print (out_class_file)
        for c in classList:
            out_class_file.write(c+'\n')

        out_class_file.close()
        out_file.close()



class YoloReader:

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
        self.parseYoloFormat()

    def getShapes(self):
        return self.shapes

    def addShape(self, label, points, difficult):
        self.shapes.append((label, points, None, None, difficult))

    def yoloLine2Shape(self, classIndex, x1, y1, x2, y2, x3, y3, x4, y4):
        label = self.classes[int(classIndex)]

        # Преобразование координат в пиксели изображения
        x1, y1 = int(float(x1) * self.imgSize[1]), int(float(y1) * self.imgSize[0])
        x2, y2 = int(float(x2) * self.imgSize[1]), int(float(y2) * self.imgSize[0])
        x3, y3 = int(float(x3) * self.imgSize[1]), int(float(y3) * self.imgSize[0])
        x4, y4 = int(float(x4) * self.imgSize[1]), int(float(y4) * self.imgSize[0])

        points = [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
        return label, points

    def parseYoloFormat(self):
        with open(self.filepath, 'r') as bndBoxFile:
            for bndBox in bndBoxFile:
                parts = bndBox.strip().split(' ')
                if len(parts) == 9:
                    classIndex = parts[0]
                    coords = parts[1:]
                    label, points = self.yoloLine2Shape(classIndex, *coords)
                    self.addShape(label, points, False)
                else:
                    raise ValueError(f"Invalid line format: {bndBox.strip()}")