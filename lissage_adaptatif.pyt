# -*- coding: utf-8 -*-
# Boite à outil Python pour le lissage adaptatif et la génération des courbes de niveau
# Auteurs : CORREC Adélie, GONZO-MASSOL Raphaël, MANDOMBOY Nolvides

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
