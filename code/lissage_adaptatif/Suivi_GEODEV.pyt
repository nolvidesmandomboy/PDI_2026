# -*- coding: utf-8 -*-
import arcpy
from arcpy.ia import *
from arcpy.sa import *


class Toolbox:
    def __init__(self):
        self.label = "Suivi GEODEV"
        self.alias = "suivi_geodev"
        self.tools = [Lissage]


class Lissage:
    def __init__(self):
        self.label = "Lissage"
        self.description = "Lissage adaptatif par combinaison de MNT deux MNT"

    def getParameterInfo(self):
        #Input = MNT LiDAR HD
        p0 = arcpy.Parameter(
            displayName="MNT en entrée",
            name="input",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input"
        )

        p1 = arcpy.Parameter(
            displayName="Raster calculé de l'écart-type en sortie",
            name="out_SD",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )

        p2 = arcpy.Parameter(
            displayName="Rayon pour l'écart-type (en cellules, type de voisinage = cercle)",
            name="radius_SD",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        p2.value = 100

        p3 = arcpy.Parameter(
            displayName="Raster avec valeurs d'écart-type normalisées par une fonction sigmoïde en sortie",
            name="out_Sig",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )

        
        p4 = arcpy.Parameter(
            displayName="Coefficient de pente de la sigmoïde (a)",
            name="coef_slop_Sig",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        p4.value = 6

        p5 = arcpy.Parameter(
            displayName="Valeur d'écart-type dans les zones de transition (k)",
            name="transi_SD",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        p5.value = 4

        p6 = arcpy.Parameter(
            displayName="MNT lissé global en sortie",
            name="out_Mean",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )
    
        p7 = arcpy.Parameter(
            displayName="Type de statistique de lissage",
            name="typ_Stat",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p7.filter.type = "ValueList"
        p7.filter.list = ["MEAN"]
        p7.value = "MEAN"

        
        p8 = arcpy.Parameter(
        displayName="Rayon pour le lissage global (en cellules, type de voisinage = cercle)",
        name="radius_Mean",
        datatype="GPLong",
        parameterType="Required",
        direction="Input"
        )
        p8.value = 15
        
        p9 = arcpy.Parameter(
            displayName="Emplacement du MNT final en sortie",
            name="output",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )


        return [p0, p1, p2, p3, p4, p5, p6, p7, p8, p9]

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True
        arcpy.CheckOutExtension("spatial")
        arcpy.CheckOutExtension("ImageAnalyst")

        in_raster     = parameters[0].valueAsText
        out_SD        = parameters[1].valueAsText
        radius_SD     = parameters[2].value
        out_Sig       = parameters[3].valueAsText
        coef_slop_Sig = parameters[4].value
        transi_SD     = parameters[5].value
        out_Mean      = parameters[6].valueAsText
        typ_Stat      = parameters[7].valueAsText
        radius_Mean   = parameters[8].value
        out_raster    = parameters[9].valueAsText
        
        
        # Focal Statistics : Écart-type, calcul de l'écart type entre chaque pixel et la valeur moyenne des pixels autour compris dans un disque
        # de rayon 100 (fixé par défaut, variable)

        messages.addMessage("Calcul de l'écart-type local...")
        Focal_Statistics = out_SD
        out_SD = arcpy.ia.FocalStatistics(
            in_raster,
            "Circle " + str(radius_SD) + " CELL",
            "STD", "DATA", 90
        )
        out_SD.save(Focal_Statistics)

        # Raster Calculator : #Normalisation des valeurs d'écart type ; raster des valeurs d'écart type entré dans la fonction sigmoide 
       
        messages.addMessage("Calcul de la sigmoïde...")
        Raster_Calculator = out_Sig
        out_Sig = 1 / (1 + Exp(-coef_slop_Sig * (out_SD - transi_SD)))
        out_Sig.save(Raster_Calculator)

        # Focal Statistics : Calcul du MNT lissé globalement par moyennage des valeurs des pixels (rayon 15 cellules, soit 7.5m)

        messages.addMessage("Calcul du lissage global...")
        Focal_Statistics_2_ = out_Mean
        out_Mean = arcpy.ia.FocalStatistics(
            in_raster,
            "Circle " + str(radius_Mean) + " CELL",
            typ_Stat, "DATA", 90
        )
        out_Mean.save(Focal_Statistics_2_)

        # Raster Calculator : Combinaison différenciée des deux MNT (lissé et non lissé)
        #via la pondération par les valeurs normalisées d'écart-type
        messages.addMessage("Fusion finale...")
        Raster_Calculator_2_ = out_raster
        mnt = arcpy.Raster(in_raster)
        out_raster = mnt * out_Sig + (1 - out_Sig) * out_Mean
        out_raster.save(Raster_Calculator_2_)

        messages.addMessage("Lissage terminé avec succès.")


if __name__ == '__main__':
    with arcpy.EnvManager(
        scratchWorkspace=r"C:\Users\Raphaël\OneDrive - univ-lyon2.fr\Bureau\ETUDES\MASTER\COURS\M1\Semestre 1\PDI\MNT\Suivi_GEODEV_2026\Suivi_GEODEV_2026\Default.gdb",
        workspace=r"C:\Users\Raphaël\OneDrive - univ-lyon2.fr\Bureau\ETUDES\MASTER\COURS\M1\Semestre 1\PDI\MNT\Suivi_GEODEV_2026\Suivi_GEODEV_2026\Default.gdb"
    ):
        tbx = Toolbox()
        tool = Lissage()
