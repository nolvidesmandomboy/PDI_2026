# -*- coding: utf-8 -*-
# Outil Python pour le lissage adaptatif et la génération des courbes de niveau
# Auteurs : CORREC Adélie, GONZO-MASSOL Raphaël, MANDOMBOY Nolvides

import arcpy
import os
from arcpy.ia import *
from arcpy.sa import *

class Lissage(object):
    def __init__(self):
        self.label = "Lissage"
        self.description = "Lissage adaptatif par combinaison de MNT deux MNT"

    def getParameterInfo(self):
        
        params = []
        
        mygdb = arcpy.Parameter(
            displayName = "Géodatabase de sortie",
            name = "gdb_sortie",
            datatype= "DEWorkspace",
            parameterType = "Required",
            direction = "Input"
        )

        # MNT en entrée
        p0 = arcpy.Parameter(
            displayName="MNT en entrée",
            name="input",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input"
        )
        
        # MNT ré-échantillonné
        p1 = arcpy.Parameter(
            displayName="MNT ré-échantillonné en sortie",
            name="out_Resample",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )
        
        # Taille de rééchantillonnage
        p2 = arcpy.Parameter(
            displayName="Taille de rééchantillonage (en mètres)",
            name="resampleSize",
            datatype="GPString",
            parameterType="Required",  
            direction="Input"
        )
        p2.value = "2.5"

        # Raster calculé de l'écart-type en sortie
        p3 = arcpy.Parameter(
            displayName="Raster calculé de l'écart-type en sortie",
            name="out_SD",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )
        p3.value = 'Raster_ET'

        # Rayon pour l'écart-type
        p4 = arcpy.Parameter(
            displayName="Rayon pour l'écart-type (en cellules, type de voisinage = cercle)",
            name="radius_SD",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        p4.value = 100

        # Normalisation
        p5 = arcpy.Parameter(
            displayName="Raster avec valeurs d'écart-type normalisées par une fonction sigmoïde en sortie",
            name="out_Sig",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )
        p5.value = 'Raster_ET_norma'

        # Coefficient pente normalisation (a)
        p6 = arcpy.Parameter(
            displayName="Coefficient de pente de la sigmoïde (a)",
            name="coef_slop_Sig",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        p6.value = 6

        # Paramètre k sigmoide
        p7 = arcpy.Parameter(
            displayName="Valeur d'écart-type dans les zones de transition (k)",
            name="transi_SD",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        p7.value = 4

        # MNT global lissé 
        p8 = arcpy.Parameter(
            displayName="MNT lissé global en sortie",
            name="out_Mean",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )
        p8.value = 'MNT_lisse_global'
    
        # Choix stat de lissage
        p9 = arcpy.Parameter(
            displayName="Type de statistique de lissage",
            name="typ_Stat",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p9.filter.type = "ValueList"
        p9.filter.list = ["MEAN"] 
        p9.value = "MEAN"

        # Rayon lissage global
        p10 = arcpy.Parameter(
            displayName="Rayon pour le lissage global (en cellules, type de voisinage = cercle)",
            name="radius_Mean",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        p10.value = 20
        
        # Nom mnt final en sortie 
        p11 = arcpy.Parameter(
            displayName="MNT final en sortie",
            name="output",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )
        p11.value = 'MNT_final'

        # Choix de suppression des fichiers intermédiaires 
        p12 = arcpy.Parameter(
            displayName= 'Supprimer les fichiers intermédiaires après le traitement',
            name='delete_inter',
            datatype='GPBoolean',
            parameterType='Optional',
            direction='Input'
        )
        p12.value=True

        # Choix de générer les courbes de niveau
        p13 = arcpy.Parameter(
            displayName= 'Générer les courbes de niveau',
            name='genere_courbes',
            datatype='GPBoolean',
            parameterType='Optional',
            direction='Input'
        )
        p13.value=True

        # Ajout de TOUS les paramètres dans le bon ordre
        params.extend([mygdb, p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13])
        return params
    
    def isLicensed(self):
        return True
    
    def execute(self, parameters, messages):
        mygdb          = parameters[0].valueAsText #mygpb
        
        in_raster      = parameters[1].valueAsText #p0
        
        out_Resample   = parameters[2].valueAsText #p1
        
        resample_raw   = parameters[3].valueAsText #p2
        resampleSize   = float(resample_raw.replace(",", "."))
        
        out_SD         = parameters[4].valueAsText #p3
        radius_SD      = parameters[5].value #p4
        
        out_Sig        = parameters[6].valueAsText #p5
        coef_slop_Sig  = parameters[7].value #p6
        transi_SD      = parameters[8].value #p7
        
        out_Mean       = parameters[9].valueAsText #p8
        typ_Stat       = parameters[10].valueAsText #p9
        radius_Mean    = parameters[11].value #p10
        
        out_raster     = parameters[12].valueAsText #p11
        
        delete_inter   = parameters[13].value #p12
        
        genere_courbes = parameters[14].value #p13

        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = mygdb

        arcpy.CheckOutExtension("spatial")
        arcpy.CheckOutExtension("ImageAnalyst")

        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        toolbox_path = os.path.join(script_dir, "courbes_de_niveau.pyt")
        
        #toolbox_path = r"..\PDI_2026\courbes_de_niveau.pyt"
        arcpy.ImportToolbox(toolbox_path, "courbes")
        arcpy.AddMessage(str(arcpy.ListTools()))


        # 7 ou 6 traitements, éventuellement 1 suppression (fichiers intermédiaires)
        if delete_inter and genere_courbes :
            nb_etapes=7
        elif delete_inter or genere_courbes :
            nb_etapes= 6   
        else:
            nb_etapes = 5
            
        arcpy.SetProgressor(
            'Step', 
            'Lissage adaptatif en cours...', 
            0, 
            nb_etapes, 
            1
        )
        
        
        # Resample : Ré-échantillonnage du MNT inital avec les valeurs indiquées par l'utilisateur
        arcpy.SetProgressorLabel("Ré-échantillonnage du MNT...")
        arcpy.management.Resample(
            in_raster,
            out_Resample,
            resampleSize,
            "NEAREST"
        )
        arcpy.SetProgressorPosition()
        
        
        # Focal Statistics : Écart-type, calcul de l'écart type entre chaque pixel et la valeur moyenne des pixels autour compris dans un disque de rayon 100 (fixé par défaut, variable)
        arcpy.SetProgressorLabel("Calcul de l'écart-type local...")
        messages.addMessage("Calcul de l'écart-type local...")
        Focal_Statistics = out_SD
        out_SD = arcpy.ia.FocalStatistics(
            out_Resample, ## on met le mnt reechantillonné
            "Circle " + str(radius_SD) + " CELL",
            "STD", "DATA", 90
        )
        out_SD.save(Focal_Statistics)
        arcpy.SetProgressorPosition()

        # Raster Calculator : #Normalisation des valeurs d'écart type ; raster des valeurs d'écart type entré dans la fonction sigmoide 
        arcpy.SetProgressorLabel("Normalisation des valeurs d'écart-type...")
        messages.addMessage("Normalisation des valeurs d'écart-type...")
        Raster_Calculator = out_Sig
        out_Sig = 1 / (1 + Exp(-coef_slop_Sig * (out_SD - transi_SD)))
        out_Sig.save(Raster_Calculator)
        arcpy.SetProgressorPosition()

        # Focal Statistics : Calcul du MNT lissé globalement par moyennage des valeurs des pixels (rayon 15 cellules, soit 7.5m)
        arcpy.SetProgressorLabel(" Calcul du lissage global...")
        messages.addMessage("Calcul du lissage global...")
        Focal_Statistics_2_ = out_Mean
        out_Mean = arcpy.ia.FocalStatistics(
            out_Resample, ## on met le mnt reechantillonné
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
        mnt = arcpy.Raster(out_Resample)  ## on met le mnt reechantillonné à la place du MNT initial
        out_raster = mnt * out_Sig + (1 - out_Sig) * out_Mean
        out_raster.save(Raster_Calculator_2_)
        arcpy.SetProgressorPosition()
        messages.addMessage("Lissage terminé avec succès.")

        #Appel de l'algorithme de génération des courbes de niveau
        # Étape 5 — Courbes de niveau (optionnel)
        if genere_courbes:
            arcpy.SetProgressorLabel("Génération des courbes de niveau...")
            messages.addMessage("Génération des courbes de niveau...")
            arcpy.GenererCourbes_courbes(
                Raster_Calculator_2_,
                0.5,
                15,
                0.5,
                mygdb,
                5,
                60,
                "Courbes_Finales"
            )
            arcpy.SetProgressorPosition()
            messages.addMessage("Courbes générées avec succès.")

        if delete_inter:
            arcpy.SetProgressorLabel('Supression des fichiers intermédiaires...')
            messages.addMessage('Supression des fichiers intermédiaires...')
            for path in [Focal_Statistics, Raster_Calculator, Focal_Statistics_2_]:
                if arcpy.Exists (path):
                    arcpy.Delete_management(path)
                    messages.addMessage(f'- Supprimé : {path}')
            arcpy.SetProgressorPosition()
            messages.addMessage('Fichiers intermédiaires supprimés.')
        
        messages.addMessage("Lissage terminé avec succès.")