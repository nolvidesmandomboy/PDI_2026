import arcpy
from arcpy.ia import *
from arcpy.sa import *

class Lissage(object):
    def __init__(self):
        self.label = "Lissage"
        self.description = "Lissage adaptatif par combinaison de MNT deux MNT"

    def getParameterInfo(self):
        
        params = []
        
        # 0 - MNT en entrée
        p0 = arcpy.Parameter(
            displayName="MNT en entrée",
            name="input",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input"
        )

        # 1 - Raster calculé de l'écart-type en sortie
        p1 = arcpy.Parameter(
            displayName="Raster calculé de l'écart-type en sortie",
            name="out_SD",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )

        # 2 -
        p2 = arcpy.Parameter(
            displayName="Rayon pour l'écart-type (en cellules, type de voisinage = cercle)",
            name="radius_SD",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        p2.value = 100

        # 3 -
        p3 = arcpy.Parameter(
            displayName="Raster avec valeurs d'écart-type normalisées par une fonction sigmoïde en sortie",
            name="out_Sig",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )

        # 4 -
        p4 = arcpy.Parameter(
            displayName="Coefficient de pente de la sigmoïde (a)",
            name="coef_slop_Sig",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        p4.value = 6

        # 5 -
        p5 = arcpy.Parameter(
            displayName="Valeur d'écart-type dans les zones de transition (k)",
            name="transi_SD",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        p5.value = 4

        # 6 -
        p6 = arcpy.Parameter(
            displayName="MNT lissé global en sortie",
            name="out_Mean",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )
    
        # 7 -
        p7 = arcpy.Parameter(
            displayName="Type de statistique de lissage",
            name="typ_Stat",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p7.filter.type = "ValueList"
        p7.filter.list = ["MEAN", "GAUSSIAN"] ## à modifier pour le GAUSSIAN
        p7.value = "MEAN"

        # 8 - 
        p8 = arcpy.Parameter(
        displayName="Rayon pour le lissage global (en cellules, type de voisinage = cercle)",
        name="radius_Mean",
        datatype="GPLong",
        parameterType="Required",
        direction="Input"
        )
        p8.value = 15
        
        # 9 -
        p9 = arcpy.Parameter(
            displayName="Emplacement du MNT final en sortie",
            name="output",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )

        p10 = arcpy.Parameter(
            displayName= 'Supprimer les fichiers intermédiaires après le traitement',
            name='delete_inter',
            datatype='GPBoolean',
            parameterType='Optional',
            direction='Input'
        )
        p10.value=True
        
        params.extend([p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10])
        return params
    
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
        delete_inter  = parameters[10].value
        
        #4 traitements, éventuellement 1 suppression (fichiers intermédiaires)
        nb_etapes=5 if delete_inter else 4
        arcpy.SetProgressor('Step', 'Lissage adaptatif en cours...', 0, nb_etapes, 1)

        # Focal Statistics : Écart-type, calcul de l'écart type entre chaque pixel et la valeur moyenne des pixels autour compris dans un disque
        # de rayon 100 (fixé par défaut, variable)
        arcpy.SetProgressorLabel("Calcul de l'écart-type local...")
        messages.addMessage("Calcul de l'écart-type local...")
        Focal_Statistics = out_SD
        out_SD = arcpy.ia.FocalStatistics(
            in_raster,
            "Circle " + str(radius_SD) + " CELL",
            "STD", "DATA", 90
        )
        out_SD.save(Focal_Statistics)
        arcpy.SetProgressorPosition()

        # Raster Calculator : #Normalisation des valeurs d'écart type ; raster des valeurs d'écart type entré dans la fonction sigmoide 
       
        arcpy.SetProgressorLabel("Etape 2/4 Normalisation des valeurs d'écart-type...")
        messages.addMessage("Normalisation des valeurs d'écart-type...")
        Raster_Calculator = out_Sig
        out_Sig = 1 / (1 + Exp(-coef_slop_Sig * (out_SD - transi_SD)))
        out_Sig.save(Raster_Calculator)
        arcpy.SetProgressorPosition()

        # Focal Statistics : Calcul du MNT lissé globalement par moyennage des valeurs des pixels (rayon 15 cellules, soit 7.5m)
        arcpy.SetProgressorLabel("Etape 3/4 Calcul du lissage global...")
        messages.addMessage("Calcul du lissage global...")
        Focal_Statistics_2_ = out_Mean
        out_Mean = arcpy.ia.FocalStatistics(
            in_raster,
            "Circle " + str(radius_Mean) + " CELL",
            typ_Stat, "DATA", 90
        )
        out_Mean.save(Focal_Statistics_2_)
        arcpy.SetProgressorPosition()

        # Raster Calculator : Combinaison différenciée des deux MNT (lissé et non lissé)
        #via la pondération par les valeurs normalisées d'écart-type
        arcpy.SetProgressorLabel("Combinaison des rasters...")
        messages.addMessage("Combinaison des rasters...")
        Raster_Calculator_2_ = out_raster
        mnt = arcpy.Raster(in_raster)
        out_raster = mnt * out_Sig + (1 - out_Sig) * out_Mean
        out_raster.save(Raster_Calculator_2_)
        arcpy.SetProgressorPosition()

        messages.addMessage("Lissage terminé avec succès.")


        if delete_inter:
            arcpy.SetProgressorLabel('Supression des fichiers intermédiaires...')
            messages.addMessage('Supression des fichiers intermédiaires...')
            for path in [Focal_Statistics, Raster_Calculator, Focal_Statistics_2_]:
                if arcpy.Exists (path):
                    arcpy.Delete_management(path)
                    messages.addMessage(f'- Supprimé : {path}')
            arcpy.SetProgressorPosition()
            messages.addMessage('Fichiers intermédiaires supprimés.')
        
        # arcpy.ResetProgressor()
