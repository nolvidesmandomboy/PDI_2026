# -*- coding: utf-8 -*-
import arcpy
from arcpy.ia import *
from arcpy.sa import *
from lissage import Lissage


class Toolbox(object):
    def __init__(self):
        self.label = "Suivi GEODEV"
        self.alias = "suivi_geodev"
        self.tools = [Lissage]

if __name__ == '__main__':
        tbx = Toolbox()
        tool = Lissage()