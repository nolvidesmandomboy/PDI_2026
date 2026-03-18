import arcpy
from arcpy.ia import *
from arcpy.sa import *

arcpy.ImportToolbox("C:\Suivi_GEODEV_2026\Suivi_GEODEV_2026\code\courbes_de_niveau.pyt")


#Algorithme avec focal statistiques Cercles, rayon à choisir par l'utilisateur, longueur min 60

MNT_input= arcpy.GetParameterAsText(0)
Rayon= arcpy.GetParameterAsText(1)


def Model():  # Model

    # To allow overwriting outputs change overwriteOutput option to True.
    arcpy.env.overwriteOutput = True

    # Check out any necessary licenses.
    arcpy.CheckOutExtension("spatial")
    arcpy.CheckOutExtension("ImageAnalyst")


    MNT = arcpy.Raster(MNT_input)
    Projet_info_gdb = "C:\\Users\\adeli\\OneDrive\\Documents\\ArcGIS\\Projects\\Projet_info\\Projet_info.gdb"
    courbes_de_niveau_pyt = "C:\\Suivi_GEODEV_2026\\Suivi_GEODEV_2026\\code\\courbes_de_niveau.pyt"

    # Process: Focal Statistics (Focal Statistics) (ia)
    FocalSt_MNT21 = "C:\\Users\\adeli\\OneDrive\\Documents\\ArcGIS\\Projects\\Projet_info\\Projet_info.gdb\\FocalSt_MNT21"
    Focal_Statistics = FocalSt_MNT21
    FocalSt_MNT21 = arcpy.ia.FocalStatistics(MNT, f"Circle {Rayon} CELL", "MEAN", "DATA", 90)
    FocalSt_MNT21.save(Focal_Statistics)


    # Process: Générer courbes de niveau (Générer courbes de niveau) (courbes)
    if courbes_de_niveau_pyt:
        arcpy.courbes.GenererCourbes(mnt_entree=FocalSt_MNT21, cell_size=1, simplify_tolerance=0.5, smooth_tolerance=15, simplify_tolerance_bis=0.5, gdb_sortie=Projet_info_gdb, equidistance=5, longueur_min=60, nom_sortie=f"Courbes_Finales_focalstat_circle_r{Rayon}")

if __name__ == '__main__':
    # Global Environment settings
    with arcpy.EnvManager(scratchWorkspace="C:\\Users\\adeli\\OneDrive\\Documents\\ArcGIS\\Projects\\Projet_info\\Projet_info.gdb", workspace="C:\\Users\\adeli\\OneDrive\\Documents\\ArcGIS\\Projects\\Projet_info\\Projet_info.gdb"):
        Model()