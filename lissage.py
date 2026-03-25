import arcpy
from arcpy.ia import *
from arcpy.sa import *

class Lissage(object):
    def __init__(self):
        self.label = "Lissage"
        self.description = "Lissage adaptatif par combinaison de MNT deux MNT"

    def getParameterInfo(self):
        
        params = []
        
        mygdb = arcpy.Parameter(
            displayName = " Géodatabase de sortie",
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

        # Raster calculé de l'écart-type en sortie
        p1 = arcpy.Parameter(
            displayName="Raster calculé de l'écart-type en sortie",
            name="out_SD",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )
        p1.value = 'Raster_ET'

        # Rayon
        p2 = arcpy.Parameter(
            displayName="Rayon pour l'écart-type (en cellules, type de voisinage = cercle)",
            name="radius_SD",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        p2.value = 100

        # Normalisation
        p3 = arcpy.Parameter(
            displayName="Raster avec valeurs d'écart-type normalisées par une fonction sigmoïde en sortie",
            name="out_Sig",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )
        p3.value = 'Raster_ET_norma'

        # Coefficiant pente normalisation (a)
        p4 = arcpy.Parameter(
            displayName="Coefficient de pente de la sigmoïde (a)",
            name="coef_slop_Sig",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        p4.value = 6

        # Paramètre k sigmoide
        p5 = arcpy.Parameter(
            displayName="Valeur d'écart-type dans les zones de transition (k)",
            name="transi_SD",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        p5.value = 4

        # MNT global lissé 
        p6 = arcpy.Parameter(
            displayName="MNT lissé global en sortie",
            name="out_Mean",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output"
        )
        p6.value = 'MNT_lisse_global'
    
        # Choix stat de lissage
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

        # Rayon lissage global
        p8 = arcpy.Parameter(
        displayName="Rayon pour le lissage global (en cellules, type de voisinage = cercle)",
        name="radius_Mean",
        datatype="GPLong",
        parameterType="Required",
        direction="Input"
        )
        p8.value = 15
        
        # Nom mnt final en sortie 
        p9 = arcpy.Parameter(
        displayName="MNT final en sortie",
        name="output",
        datatype="DERasterDataset",
        parameterType="Required",
        direction="Output"
    )
        p9.value = 'MNT_final'

        # Choix de suppression des fichiers intermédiaires 
        p10 = arcpy.Parameter(
            displayName= 'Supprimer les fichiers intermédiaires après le traitement',
            name='delete_inter',
            datatype='GPBoolean',
            parameterType='Optional',
            direction='Input'
        )
        p10.value=True

        # Choix de générer les courbes de niveau
        p11 = arcpy.Parameter(
            displayName= 'Générer les courbes de niveau',
            name='genere_courbes',
            datatype='GPBoolean',
            parameterType='Optional',
            direction='Input'
        )
        p11.value=True

        params.extend([mygdb, p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11])
        return params
    
    def isLicensed(self):
        return True
    
    def execute(self, parameters, messages):
        import os

        mygdb         = parameters[0].valueAsText
        in_raster     = parameters[1].valueAsText
        out_SD        = parameters[2].valueAsText
        radius_SD     = parameters[3].value
        out_Sig       = parameters[4].valueAsText
        coef_slop_Sig = parameters[5].value
        transi_SD     = parameters[6].value
        out_Mean      = parameters[7].valueAsText
        typ_Stat      = parameters[8].valueAsText
        radius_Mean   = parameters[9].value
        out_raster    = parameters[10].valueAsText
        delete_inter  = parameters[11].value
        genere_courbes = parameters[12].value

        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = mygdb

        arcpy.CheckOutExtension("spatial")
        arcpy.CheckOutExtension("ImageAnalyst")

        
        # script_dir = os.path.dirname(os.path.abspath(__file__))
        # toolbox_path = os.path.join(script_dir, "courbes_de_niveau.pyt")
        toolbox_path = r"C:\PDI_2026\courbes_de_niveau.pyt"
        arcpy.ImportToolbox(toolbox_path, "courbes")
        arcpy.AddMessage(str(arcpy.ListTools()))

        # 5 ou 6 traitements, éventuellement 1 suppression (fichiers intermédiaires)
        if delete_inter and genere_courbes :
            nb_etapes=6
        elif delete_inter or genere_courbes :
            nb_etapes= 5   
        else:
            nb_etapes = 4
            
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

        #Appel de l'algorithme de génération des courbes de niveau
               # Étape 5 — Courbes de niveau (optionnel)
        if genere_courbes:
            arcpy.SetProgressorLabel("Génération des courbes de niveau...")
            messages.addMessage("Génération des courbes de niveau...")
            arcpy.GenererCourbes_courbes(
                # mnt_entree=in_raster,
                # simplify_tolerance=0.5,
                # smooth_tolerance=15,
                # gdb_sortie=mygdb,
                # simplify_tolerance_bis=0.5,
                # equidistance=5,
                # longueur_min=60,
                # nom_sortie="Courbes_Finales"
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
        
        # arcpy.ResetProgressor()
