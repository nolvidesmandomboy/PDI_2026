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
        self.description = "Lissage adaptatif par sigmoïde basée sur l'écart-type local"

    def getParameterInfo(self):

        p0 = arcpy.Parameter(
            displayName="MNT en entrée",
            name="input",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input"
        )

        p1 = arcpy.Parameter(
            displayName="MNT calculé de l'écart-type en sortie",
            name="out_SD",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )

        p2 = arcpy.Parameter(
            displayName="MNT normalisé par une fonction sigmoïde en sortie",
            name="out_Sig",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )

        p3 = arcpy.Parameter(
            displayName="MNT lissé global en sortie",
            name="out_Mean",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )

        p4 = arcpy.Parameter(
            displayName="MNT final en sortie",
            name="output",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )

        p5 = arcpy.Parameter(
            displayName="Rayon pour l'écart-type (en cellules)",
            name="radius_SD",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        p5.value = 100

        p6 = arcpy.Parameter(
            displayName="Rayon pour le lissage global (en cellules)",
            name="radius_Mean",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        p6.value = 15

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
            displayName="Coefficient de pente de la sigmoïde (a)",
            name="coef_slop_Sig",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        p8.value = 6

        p9 = arcpy.Parameter(
            displayName="Valeur d'écart-type dans les zones de transition (k)",
            name="transi_SD",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        p9.value = 4

        return [p0, p1, p2, p3, p4, p5, p6, p7, p8, p9]

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True
        arcpy.CheckOutExtension("spatial")
        arcpy.CheckOutExtension("ImageAnalyst")

        in_raster     = parameters[0].valueAsText
        out_SD        = parameters[1].valueAsText
        out_Sig       = parameters[2].valueAsText
        out_Mean      = parameters[3].valueAsText
        out_raster    = parameters[4].valueAsText
        radius_SD     = parameters[5].value
        radius_Mean   = parameters[6].value
        typ_Stat      = parameters[7].valueAsText
        coef_slop_Sig = parameters[8].value
        transi_SD     = parameters[9].value

        # Focal Statistics : Écart-type local
        messages.addMessage("Calcul de l'écart-type local...")
        Focal_Statistics = out_SD
        out_SD = arcpy.ia.FocalStatistics(
            in_raster,
            "Circle " + str(radius_SD) + " CELL",
            "STD", "DATA", 90
        )
        out_SD.save(Focal_Statistics)

        # Raster Calculator : Sigmoïde
        messages.addMessage("Calcul de la sigmoïde...")
        Raster_Calculator = out_Sig
        out_Sig = 1 / (1 + Exp(-coef_slop_Sig * (out_SD - transi_SD)))
        out_Sig.save(Raster_Calculator)

        # Focal Statistics : Lissage global
        messages.addMessage("Calcul du lissage global...")
        Focal_Statistics_2_ = out_Mean
        out_Mean = arcpy.ia.FocalStatistics(
            in_raster,
            "Circle " + str(radius_Mean) + " CELL",
            typ_Stat, "DATA", 90
        )
        out_Mean.save(Focal_Statistics_2_)

        # Raster Calculator : Fusion finale
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
