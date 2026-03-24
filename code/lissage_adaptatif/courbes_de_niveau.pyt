# -*- coding: utf-8 -*-
# Toolbox Python pour la génération de courbes de niveau
# Auteur : ChatGPT + Script utilisateur
# Version : 1.1

import arcpy
import os
import re

class Toolbox(object):
    def __init__(self):
        self.label = "Courbes de Niveau"
        self.alias = "courbes"
        self.tools = [GenererCourbes, AttribuerAltitudeDXF, VerifierOrientationTalus, DecouperCourbesGlaciers, DetecterCuvettes, JonctionCourbes]

class GenererCourbes(object):
    def __init__(self):
        self.label = "Générer courbes de niveau"
        self.description = "Génère des courbes de niveau à partir d’un MNT avec simplification, lissage, orientation et filtrage."
        self.canRunInBackground = True

    def getParameterInfo(self):
        params = []

        # 0 - MNT en entrée
        p0 = arcpy.Parameter(
            displayName="MNT en entrée",
            name="mnt_entree",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")

        # 1 - Taille de cellule (résolution resample)
        p1 = arcpy.Parameter(
            displayName="Taille de rééchantillonage (mètres)",
            name="cell_size",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        # 2 - Tolérance SimplifyLine
        p2 = arcpy.Parameter(
            displayName="Tolérance SimplifyLine (mètres)",
            name="simplify_tolerance",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        # 3 - Tolérance SmoothLine
        p3 = arcpy.Parameter(
            displayName="Tolérance SmoothLine (mètres)",
            name="smooth_tolerance",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        
        # 4 - Tolérance SimplifyLine après
        p2bis = arcpy.Parameter(
            displayName="Tolérance SimplifyLine après lissage (mètres)",
            name="simplify_tolerance_bis",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        # 5 - Géodatabase de sortie
        p4 = arcpy.Parameter(
            displayName="Géodatabase de sortie",
            name="gdb_sortie",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        # 6 - Équidistance des courbes
        p5 = arcpy.Parameter(
            displayName="Équidistance des courbes (mètres)",
            name="equidistance",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        p5.value = 10  # valeur par défaut

        # 7 - Longueur minimale des courbes (filtrage final)
        p6 = arcpy.Parameter(
            displayName="Longueur minimale des courbes (mètres)",
            name="longueur_min",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        p6.value = 0  # pas de filtrage par défaut

        # 8 - Nom de la couche finale
        p7 = arcpy.Parameter(
            displayName="Nom de la couche finale",
            name="nom_sortie",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        p7.value = "Courbes_Finales"

        params.extend([p0, p1, p2, p3, p2bis, p4, p5, p6, p7])
        return params

    def execute(self, parameters, messages):
        # Récupération des paramètres
        MNTentree = parameters[0].valueAsText
        cell_size = int(parameters[1].value)
        simplify_tolerance = float(parameters[2].value)
        smooth_tolerance = float(parameters[3].value)
        simplify_tolerance_bis = float(parameters[4].value)
        Mygdb = parameters[5].valueAsText
        equidistance = int(parameters[6].value)
        longueur_min = float(parameters[7].value) if parameters[7].value else 0
        nom_sortie = parameters[8].valueAsText

        # Activer overwrite
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = Mygdb

        # Variables internes
        ResampleName = "TMP_Resample"
        courbes = "TMP_Courbes"
        courbesFilt = "TMP_CourbesFilt"
        courbesSmooth = "TMP_CourbesSmooth"
        courbesFinal = "TMP_CourbesFinal"
        symbo = "SYMBO"
        cmaitr = "TMP_CourbesMaitresses"
        bufCourb_G = "TMP_Courbes_G"
        am_G = "TMP_AltMoy_G"
        bufCourb_D = "TMP_Courbes_D"
        am_D = "TMP_AltMoy_D"
        angle = "ANGLE"

        # --- Étape 1 : Resample ---
        arcpy.AddMessage(f"Création du MNT resample ({cell_size} m)")
        arcpy.management.Resample(MNTentree, ResampleName,
                                  cell_size=f"{cell_size} {cell_size}",
                                  resampling_type="NEAREST")

        # --- Étape 2 : Courbes de niveau ---
        arcpy.AddMessage(f"Calcul des courbes (équidistance {equidistance} m)")
        arcpy.ddd.ContourWithBarriers(ResampleName, courbes, None, "POLYLINES",
                                      None, "NO_EXPLICIT_VALUES_ONLY", 0, equidistance, equidistance*5, [], 1)

        arcpy.management.AlterField(courbes, "Contour", "Altitude", "Altitude")

        # --- Étape 3 : Simplification et lissage ---
        arcpy.AddMessage("Simplification et lissage")
        arcpy.cartography.SimplifyLine(courbes, courbesFilt, "POINT_REMOVE",
                                       f"{simplify_tolerance} Meters", "RESOLVE_ERRORS", "NO_KEEP")

        arcpy.cartography.SmoothLine(courbesFilt, courbesSmooth,
                                     "PAEK", f"{smooth_tolerance} Meters", "FIXED_CLOSED_ENDPOINT")

        arcpy.cartography.SimplifyLine(courbesSmooth, courbesFinal,
                                       "POINT_REMOVE", f"{simplify_tolerance_bis} Meters", "RESOLVE_ERRORS", "NO_KEEP")

        # Ajout champ symbo
        arcpy.management.AddField(courbesFinal, symbo, "TEXT", field_length=20)
        expression = "getClass(!Type!)"
        codeblock = """
def getClass(typ):
    if typ == 1:
        return "CNV_NORMALE"
    if typ == 2:
        return "CNV_MAITRESSE"
    else:
        return "CNV_INTERCALAIRE"
"""
        arcpy.management.CalculateField(courbesFinal, symbo, expression, "PYTHON3", codeblock)

        # --- Étape 4 : Orientation ---
        requete = f"{symbo} = 'CNV_MAITRESSE'"
        arcpy.management.MakeFeatureLayer(courbesFinal, cmaitr, where_clause=requete)

        arcpy.analysis.Buffer(cmaitr, bufCourb_G, 5, "LEFT", "FLAT")
        arcpy.analysis.Buffer(cmaitr, bufCourb_D, 5, "RIGHT", "FLAT")

        arcpy.sa.ZonalStatisticsAsTable(bufCourb_G, "ORIG_FID", MNTentree, am_G, "DATA", "MEAN")
        arcpy.sa.ZonalStatisticsAsTable(bufCourb_D, "ORIG_FID", MNTentree, am_D, "DATA", "MEAN")

        arcpy.management.AlterField(am_G, "MEAN", "ALT_G", "ALT_G")
        arcpy.management.AlterField(am_D, "MEAN", "ALT_D", "ALT_D")

        arcpy.management.JoinField(courbesFinal, "OBJECTID", am_G, "ORIG_FID", "ALT_G")
        arcpy.management.JoinField(courbesFinal, "OBJECTID", am_D, "ORIG_FID", "ALT_D")

        arcpy.management.AddField(courbesFinal, "SENS", "SHORT")

        with arcpy.da.UpdateCursor(courbesFinal, ["ALT_G", "ALT_D", "SENS"]) as ucursor:
            for row in ucursor:
                if row[0] and row[1]:
                    row[2] = -1 if row[1] > row[0] else 1
                    ucursor.updateRow(row)

        arcpy.management.MakeFeatureLayer(courbesFinal, "courbes_a_inverser", "SENS = -1")
        arcpy.edit.FlipLine("courbes_a_inverser")

        # # --- Étape 5 : Filtrage longueur ---
        # if longueur_min > 0:
        #     arcpy.AddMessage(f"Filtrage des courbes de moins de {longueur_min} m")
        #     arcpy.management.MakeFeatureLayer(courbesFinal, "courbes_layer")
        #     requete = f"Shape_Length >= {longueur_min}"
        #     arcpy.management.SelectLayerByAttribute("courbes_layer", "NEW_SELECTION", requete)
        #     courbesFiltrees = "TMP_CourbesFiltrees"
        #     arcpy.management.CopyFeatures("courbes_layer", courbesFiltrees)
        #     courbesFinal = courbesFiltrees
        #     arcpy.AddMessage("Filtrage terminé.")

        # --- Étape 6 : Ajout du champ ANGLE pour la symbologie ---
        # Ajout champ symbo
        arcpy.management.AddField(courbesFinal, angle, "SHORT")
        expression2 = "getClass(!SENS!)"
        codeblock2 = """
def getClass(typ):
    if typ == -1:
        return 180
    else:
        return 0
"""
        arcpy.management.CalculateField(courbesFinal, angle, expression2, "PYTHON3", codeblock2)


        # --- Étape finale : Export sous nom choisi ---
        sortie_finale = os.path.join(Mygdb, nom_sortie)
        if arcpy.Exists(sortie_finale):
            arcpy.management.Delete(sortie_finale)
        arcpy.management.CopyFeatures(courbesFinal, sortie_finale)

        # --- Nettoyage complet ---
        for tmp in [ResampleName, courbes, courbesFilt, courbesSmooth,
                    bufCourb_G, bufCourb_D, am_G, am_D, courbesFinal]:
            if arcpy.Exists(tmp):
                arcpy.management.Delete(tmp)

        arcpy.AddMessage(f"Traitement terminé. Résultat final : {sortie_finale}")


class AttribuerAltitudeDXF(object):
    def __init__(self):
        self.label = "Attribuer altitude aux courbes DXF"
        self.description = "Ajoute un champ 'Altitude' aux polylignes DXF en récupérant la valeur depuis un MNT."
        self.canRunInBackground = True

    def getParameterInfo(self):
        params = []

        # 0 - MNT en entrée
        p0 = arcpy.Parameter(
            displayName="MNT en entrée",
            name="mnt_entree",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")

        # 1 - Courbes DXF en entrée (DXF ou classe d'entités lignes)
        p1 = arcpy.Parameter(
            displayName="Courbes DXF (fichier .dxf ou classe d'entités lignes)",
            name="courbes_dxf",
            datatype="DEFile",  # accepte soit un DXF, soit une FC
            parameterType="Required",
            direction="Input")

        # 2 - Méthode d'échantillonnage
        p2 = arcpy.Parameter(
            displayName="Méthode (MOYENNE, MEDIANE, MIN, MAX)",
            name="method",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        p2.filter.type = "ValueList"
        p2.filter.list = ["MOYENNE", "MEDIANE", "MIN", "MAX"]
        p2.value = "MOYENNE"

        # 3 - Géodatabase de sortie
        p3 = arcpy.Parameter(
            displayName="Géodatabase de sortie",
            name="gdb_sortie",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        # 4 - Nom de la couche finale
        p4 = arcpy.Parameter(
            displayName="Nom de la couche finale",
            name="nom_sortie",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        p4.value = "Courbes_DXF_Altitude"

        params.extend([p0, p1, p2, p3, p4])
        return params

    def execute(self, parameters, messages):
        MNTentree = parameters[0].valueAsText
        entree = parameters[1].valueAsText
        method = parameters[2].valueAsText
        Mygdb = parameters[3].valueAsText
        nom_sortie = parameters[4].valueAsText

        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = Mygdb

        # Vérif extension
        arcpy.AddMessage("Vérification de l'extension Spatial Analyst...")
        arcpy.CheckOutExtension("Spatial")

        # 1 Déterminer la source polyligne (depuis DXF ou FC)
        arcpy.AddMessage("Préparation des courbes...")
        courbes_src = None

        if entree.lower().endswith(".dxf"):
            arcpy.AddMessage("DXF détecté, conversion en géodatabase...")
            # Convertit le DXF dans un Feature Dataset nommé 'CAD'
            # Syntaxe positionnelle OBLIGATOIRE
            arcpy.conversion.CADToGeodatabase(entree, Mygdb, "CAD", "200")

            # Selon les versions, le nom peut être 'Polyline' OU 'CAD_Lines'
            candidats = [
                os.path.join(Mygdb, "CAD", "Polyline"),
                os.path.join(Mygdb, "CAD", "CAD_Lines")
            ]
            for c in candidats:
                if arcpy.Exists(c):
                    courbes_src = c
                    break

            if courbes_src is None:
                arcpy.AddError("Impossible de trouver la classe polyligne issue du DXF (attendu: 'CAD\\Polyline' ou 'CAD\\CAD_Lines').")
                raise arcpy.ExecuteError
        else:
            # L'utilisateur a fourni une classe d'entités / couche
            if not arcpy.Exists(entree):
                arcpy.AddError("Le chemin fourni n'existe pas.")
                raise arcpy.ExecuteError
            courbes_src = entree

        # 2 Copie de travail
        courbes_tmp = os.path.join(Mygdb, "TMP_CourbesDXF")
        if arcpy.Exists(courbes_tmp):
            arcpy.management.Delete(courbes_tmp)
        arcpy.management.CopyFeatures(courbes_src, courbes_tmp)

        # 3 Champ Altitude
        if "Altitude" not in [f.name for f in arcpy.ListFields(courbes_tmp)]:
            arcpy.management.AddField(courbes_tmp, "Altitude", "DOUBLE")

        # 4 Taille de cellule du MNT pour dimensionner un buffer fin
        arcpy.AddMessage("Calcul du buffer fin pour zones de stats...")
        
        cellx_str = arcpy.management.GetRasterProperties(MNTentree, "CELLSIZEX").getOutput(0)
        cellx = float(cellx_str.replace(",", "."))

        # buffer ~ 0.75 * taille pixel pour capturer des valeurs voisines
        buf_dist = max(cellx * 0.75, 0.001)  # sécurité

        buf_fc = os.path.join(Mygdb, "TMP_CourbesDXF_buf")
        if arcpy.Exists(buf_fc):
            arcpy.management.Delete(buf_fc)
        arcpy.analysis.Buffer(
            in_features=courbes_tmp,
            out_feature_class=buf_fc,
            buffer_distance_or_field=f"{buf_dist} Meters",
            line_side="FULL",
            line_end_type="FLAT",
            dissolve_option="NONE"
        )

        desc = arcpy.Describe(buf_fc)
        if desc.spatialReference.name == "Unknown":
            arcpy.AddMessage("Définition du système de coordonnées du buffer...")
            # On suppose que le DXF est en Lambert-93 (ou à adapter selon ton cas)
            raster_sr = arcpy.Describe(MNTentree).spatialReference
            arcpy.management.DefineProjection(buf_fc, raster_sr)

        # # --- REPROJECTION VERS LE RASTER ---
        # raster_sr = arcpy.Describe(MNTentree).spatialReference
        # buf_fc_proj = os.path.join(Mygdb, "TMP_CourbesDXF_buf_proj")
        # if arcpy.Exists(buf_fc_proj):
        #     arcpy.management.Delete(buf_fc_proj)

        # if arcpy.Describe(buf_fc).spatialReference.name != raster_sr.name:
        #     arcpy.AddMessage(f"Reprojection de {buf_fc} vers {raster_sr.name}...")
        #     arcpy.management.Project(buf_fc, buf_fc_proj, raster_sr)
        # else:
        #     buf_fc_proj = buf_fc  # déjà compatible

        # 5 ZonalStatisticsAsTable
        arcpy.AddMessage("Échantillonnage du MNT (Zonal Statistics)...")
        stats_table = os.path.join(Mygdb, "TMP_Stats")
        if arcpy.Exists(stats_table):
            arcpy.management.Delete(stats_table)

        if method == "MOYENNE":
            stat = "MEAN"
        elif method == "MEDIANE":
            stat = "MEDIAN"
        elif method == "MIN":
            stat = "MIN"
        else:
            stat = "MAX"

        arcpy.sa.ZonalStatisticsAsTable(
            in_zone_data=buf_fc,
            zone_field="ORIG_FID" if "ORIG_FID" in [f.name for f in arcpy.ListFields(buf_fc)] else "OBJECTID",
            in_value_raster=MNTentree,
            out_table=stats_table,
            ignore_nodata="DATA",
            statistics_type=stat
        )

        # 6 Préparer le champ à joindre
        champ_alt_src = stat
        if champ_alt_src not in [f.name for f in arcpy.ListFields(stats_table)]:
            arcpy.AddError(f"Le champ '{stat}' n'a pas été produit par ZonalStatisticsAsTable.")
            raise arcpy.ExecuteError

        # Renommer le champ pour éviter les collisions
        if "ALT_TMP" in [f.name for f in arcpy.ListFields(stats_table)]:
            arcpy.management.DeleteField(stats_table, ["ALT_TMP"])
        arcpy.management.AlterField(stats_table, champ_alt_src, "ALT_TMP", "ALT_TMP")

        # 7 Join des valeurs altitude sur les lignes d'origine
        # On joint via ORIG_FID si disponible dans le buffer, sinon via OBJECTID en conservant l'ordre
        zone_field = "ORIG_FID" if "ORIG_FID" in [f.name for f in arcpy.ListFields(buf_fc)] else "OBJECTID"
        arcpy.management.JoinField(courbes_tmp, "OBJECTID", stats_table, zone_field, ["ALT_TMP"])

        # 8 Calcul final dans 'Altitude'
        with arcpy.da.UpdateCursor(courbes_tmp, ["ALT_TMP", "Altitude"]) as cursor:
            for row in cursor:
                row[1] = row[0]
                cursor.updateRow(row)

        # 9 Nettoyage champ transitoire
        if "ALT_TMP" in [f.name for f in arcpy.ListFields(courbes_tmp)]:
            arcpy.management.DeleteField(courbes_tmp, ["ALT_TMP"])

        # 10 Export final
        sortie_finale = os.path.join(Mygdb, nom_sortie)
        if arcpy.Exists(sortie_finale):
            arcpy.management.Delete(sortie_finale)
        arcpy.management.CopyFeatures(courbes_tmp, sortie_finale)

        # 11 Nettoyage
        for tmp in [courbes_tmp, buf_fc, stats_table]:
            if arcpy.Exists(tmp):
                arcpy.management.Delete(tmp)

        arcpy.CheckInExtension("Spatial")
        arcpy.AddMessage(f" Altitude attribuée. Résultat : {sortie_finale}")
        

class VerifierOrientationTalus(object):
    def __init__(self):
        self.label = "Vérifier orientation des talus"
        self.description = ("Vérifie le sens des talus à partir d'un MNT : "
                            "le côté droit doit être plus bas que le côté gauche. "
                            "Les courbes sont inversées si nécessaire.")
        self.canRunInBackground = True

    def getParameterInfo(self):
        params = []

        # 0 - Talus (polylignes)
        p0 = arcpy.Parameter(
            displayName="Talus (polylignes)",
            name="talus_entree",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        # 1 - MNT associé
        p1 = arcpy.Parameter(
            displayName="MNT correspondant",
            name="mnt_entree",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")

        params.extend([p0, p1])
        return params

    def execute(self, parameters, messages):
        talus_fc = parameters[0].valueAsText
        mnt_fc = parameters[1].valueAsText

        arcpy.env.overwriteOutput = True
        gdb = arcpy.env.workspace
        messages.addMessage(f"Workspace : {gdb}")

        bufG = "TMP_Talus_G"
        bufD = "TMP_Talus_D"
        tabG = "TMP_AltG"
        tabD = "TMP_AltD"

        # Suppression des anciens champs
        for f in arcpy.ListFields(talus_fc):
            if f.name in ["ALT_G", "ALT_D", "SENS"]:
                arcpy.management.DeleteField(talus_fc, f.name)

        # Création des buffers gauche/droite
        arcpy.analysis.Buffer(talus_fc, bufG, 5, "LEFT", "FLAT")
        arcpy.analysis.Buffer(talus_fc, bufD, 5, "RIGHT", "FLAT")

        # Calcul altitude moyenne
        arcpy.sa.ZonalStatisticsAsTable(bufG, "ORIG_FID", mnt_fc, tabG, "DATA", "MEAN")
        arcpy.sa.ZonalStatisticsAsTable(bufD, "ORIG_FID", mnt_fc, tabD, "DATA", "MEAN")

        # Renommer les champs
        arcpy.management.AlterField(tabG, "MEAN", "ALT_G", "ALT_G")
        arcpy.management.AlterField(tabD, "MEAN", "ALT_D", "ALT_D")

        # Joindre sur la couche talus
        arcpy.management.JoinField(talus_fc, "OBJECTID", tabG, "ORIG_FID", ["ALT_G"])
        arcpy.management.JoinField(talus_fc, "OBJECTID", tabD, "ORIG_FID", ["ALT_D"])

        # Ajouter champ SENS
        arcpy.management.AddField(talus_fc, "SENS", "SHORT")

        # Mise à jour du sens
        with arcpy.da.UpdateCursor(talus_fc, ["ALT_G", "ALT_D", "SENS"]) as cursor:
            for row in cursor:
                if row[0] is not None and row[1] is not None:
                    row[2] = -1 if row[1] > row[0] else 1
                    cursor.updateRow(row)

        # Inversion des géométries si nécessaire
        arcpy.management.MakeFeatureLayer(talus_fc, "talus_inverser", "SENS = -1")
        arcpy.edit.FlipLine("talus_inverser")

        # Nettoyage
        for tmp in [bufG, bufD, tabG, tabD]:
            if arcpy.Exists(tmp):
                arcpy.management.Delete(tmp)

        messages.addMessage("Orientation des talus vérifiée et appliquée.")

class DecouperCourbesGlaciers(object):
    def __init__(self):
        self.label = "Découper courbes par glaciers"
        self.description = "Découpe les courbes selon une couche de glaciers et met à jour SYMBO (CVN_GLACIER_NORMALE / CVN_GLACIER_MAITRESSE) lorsque nécessaire."
        self.canRunInBackground = True

    def getParameterInfo(self):
        params = []

        p0 = arcpy.Parameter(
            displayName="Courbes de niveau",
            name="courbes_entree",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        p1 = arcpy.Parameter(
            displayName="Glaciers (polygones)",
            name="glaciers_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        p2 = arcpy.Parameter(
            displayName="Géodatabase de sortie",
            name="gdb_sortie",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        p3 = arcpy.Parameter(
            displayName="Nom de la couche finale",
            name="nom_sortie",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        p3.value = "Courbes_Glaciers"

        params.extend([p0, p1, p2, p3])
        return params

    def _basename(self, path):
        d = arcpy.Describe(path)
        try:
            return d.baseName
        except:
            return os.path.splitext(d.name)[0]

    def execute(self, parameters, messages):
        courbes_fc = parameters[0].valueAsText
        glaciers_fc = parameters[1].valueAsText
        gdb = parameters[2].valueAsText
        nom_sortie = parameters[3].valueAsText

        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = gdb

        messages.addMessage("Découpage des courbes par les glaciers...")

        # 1) Identity (découpage)
        tmp_split = os.path.join(gdb, "TMP_CourbesGlaciers")
        if arcpy.Exists(tmp_split):
            arcpy.management.Delete(tmp_split)

        arcpy.analysis.Identity(courbes_fc, glaciers_fc, tmp_split, "ONLY_FID")

        # 2) Trouver le bon champ FID_ des glaciers
        gl_base = self._basename(glaciers_fc)
        in_base = self._basename(courbes_fc)

        fid_candidates = [f.name for f in arcpy.ListFields(tmp_split) if f.name.upper().startswith("FID_")]
        fid_field = None

        # Essais directs
        for candidate in (f"FID_{gl_base}", f"FID_{os.path.splitext(gl_base)[0]}", f"FID_{gl_base.replace('.shp','')}"):
            if candidate in fid_candidates:
                fid_field = candidate
                break

        # Si échec, éliminer le FID des courbes si présent
        if fid_field is None:
            fid_in = None
            for candidate in (f"FID_{in_base}", f"FID_{os.path.splitext(in_base)[0]}"):
                if candidate in fid_candidates:
                    fid_in = candidate
                    break
            if fid_in and len(fid_candidates) >= 2:
                others = [c for c in fid_candidates if c != fid_in]
                if others:
                    fid_field = others[0]
            elif not fid_field and len(fid_candidates) == 1:
                fid_field = fid_candidates[0]

        if fid_field is None:
            raise RuntimeError("Impossible d'identifier le champ FID_ des glaciers. Champs trouvés : " + ", ".join(fid_candidates))

        # 3) S'assurer que SYMBO peut contenir les nouvelles valeurs (>= 21)
        symbo_field = None
        for f in arcpy.ListFields(tmp_split):
            if f.name.upper() == "SYMBO":
                symbo_field = f
                break
        if symbo_field is None:
            raise RuntimeError("Le champ 'SYMBO' est introuvable dans la couche issue de l'Identity.")

        if symbo_field.length < 21:
            messages.addMessage(f"Le champ SYMBO est trop court ({symbo_field.length}). Migration vers longueur 30...")
            # Ajouter un champ temporaire plus long
            if "SYMBO_TMP" in [f.name for f in arcpy.ListFields(tmp_split)]:
                arcpy.management.DeleteField(tmp_split, ["SYMBO_TMP"])
            arcpy.management.AddField(tmp_split, "SYMBO_TMP", "TEXT", field_length=30)
            arcpy.management.CalculateField(tmp_split, "SYMBO_TMP", "!SYMBO!", "PYTHON3")
            # Supprimer SYMBO et renommer SYMBO_TMP → SYMBO
            arcpy.management.DeleteField(tmp_split, ["SYMBO"])
            arcpy.management.AlterField(tmp_split, "SYMBO_TMP", "SYMBO", "SYMBO")
            messages.addMessage("Champ SYMBO migré à longueur 30.")

        # 4) Mettre à jour SYMBO selon l'intersection glacier
        with arcpy.da.UpdateCursor(tmp_split, ["SYMBO", fid_field]) as cursor:
            for row in cursor:
                fid_glacier = row[1]
                if fid_glacier != -1:  # intersecte un glacier
                    if row[0] == "CNV_MAITRESSE":
                        row[0] = "CNV_GLACIER_MAITRESSE"
                    elif row[0] == "CNV_NORMALE":
                        row[0] = "CNV_GLACIER_NORMALE"
                    # sinon on laisse les autres classes inchangées
                    cursor.updateRow(row)
                else:
                    # hors glacier: aucune modification
                    continue

        # 5) Export final
        sortie_finale = os.path.join(gdb, nom_sortie)
        if arcpy.Exists(sortie_finale):
            arcpy.management.Delete(sortie_finale)
        arcpy.management.CopyFeatures(tmp_split, sortie_finale)

        # 6) Nettoyage
        if arcpy.Exists(tmp_split):
            arcpy.management.Delete(tmp_split)

        messages.addMessage(f"Découpage terminé. Résultat : {sortie_finale}")


class DetecterCuvettes(object):
    def __init__(self):
        self.label = "Détecter cuvettes"
        self.description = "Détecte les cuvettes et sommets en comparant les altitudes intérieures et extérieures à partir du MNT."
        self.canRunInBackground = True

    def getParameterInfo(self):
        params = []

        # 0 - Couche de courbes
        p0 = arcpy.Parameter(
            displayName="Couche de courbes de niveau",
            name="courbes",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        # 1 - Polygones intermédiaires
        p1 = arcpy.Parameter(
            displayName="Polygones intermédiaires (FeatureToPolygon)",
            name="polys_inter",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        # 2 - Sortie finale
        p2 = arcpy.Parameter(
            displayName="Polygones classés",
            name="sortie_cuvettes",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        # 3 - MNT
        p3 = arcpy.Parameter(
            displayName="MNT (Modèle Numérique de Terrain)",
            name="mnt",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")
        
        # 2 - Sortie interemédiaire
        pint = arcpy.Parameter(
            displayName="int",
            name="int",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        return [p0, p1, p2, p3, pint]

    def execute(self, parameters, messages):
        courbes = parameters[0].valueAsText
        polys_inter = parameters[1].valueAsText
        sortie_cuvettes = parameters[2].valueAsText
        mnt = parameters[3].valueAsText
        pint = parameters[4].valueAsText

        arcpy.env.overwriteOutput = True
        

        # Étape 1 : conversion courbes -> polygones
        arcpy.AddMessage("Conversion des courbes fermées en polygones...")
        arcpy.management.FeatureToPolygon(courbes, polys_inter, None, "NO_ATTRIBUTES")
        oid_field = arcpy.Describe(polys_inter).OIDFieldName

        # Étape 2 : filtrer polygones sans trous
        cuvettes_ids = []
        with arcpy.da.SearchCursor(polys_inter, [oid_field, "SHAPE@"]) as cursor:
            for oid, geom in cursor:
                has_hole = False
                for part in geom:
                    if any(pnt is None for pnt in part):
                        has_hole = True
                        break
                if not has_hole:
                    cuvettes_ids.append(oid)

        arcpy.AddMessage(f"{len(cuvettes_ids)} polygones sans trous détectés")

        if not cuvettes_ids:
            arcpy.AddMessage("Aucun polygone sans trous, arrêt.")
            return


        where_clause = f"{oid_field} IN ({','.join(map(str, cuvettes_ids))})"
        arcpy.MakeFeatureLayer_management(polys_inter, "cuvettes_layer", where_clause)
        arcpy.CopyFeatures_management("cuvettes_layer", sortie_cuvettes)

       # Étape 3 : ZonalStatistics pour moyenne des polygones
        tab_stats = "TMP_tab_stats"
        arcpy.sa.ZonalStatisticsAsTable(
            sortie_cuvettes, oid_field, mnt, tab_stats, "DATA", "MEAN"
        )
        arcpy.management.AlterField(tab_stats, "MEAN", "ALT_POLY")

        # Joindre ALT_POLY
        arcpy.management.JoinField(sortie_cuvettes, oid_field, tab_stats, oid_field, ["ALT_POLY"])

        # Ajouter champs pour centroïde et type
        if "ALT_CENT" not in [f.name for f in arcpy.ListFields(sortie_cuvettes)]:
            arcpy.management.AddField(sortie_cuvettes, "ALT_CENT", "DOUBLE")
        if "TYPE" not in [f.name for f in arcpy.ListFields(sortie_cuvettes)]:
            arcpy.management.AddField(sortie_cuvettes, "TYPE", "TEXT")

        # Étape 4 : calcul altitude centroïde et classification
        with arcpy.da.UpdateCursor(sortie_cuvettes, ["SHAPE@", "ALT_POLY", "ALT_CENT", "TYPE"]) as cursor:
            for geom, alt_poly, alt_cent, type_val in cursor:
                centroid = geom.centroid
                # Altitude du centroïde
                alt_c = arcpy.GetCellValue_management(mnt, f"{centroid.X} {centroid.Y}").getOutput(0)
                if alt_c and alt_c not in ("NoData", "Nan"):
                    alt_c = float(alt_c.replace(",", "."))
                else:
                    alt_c = None
                
                # Mise à jour
                new_type = None
                if alt_poly is not None:
                    if alt_c < alt_poly:
                        new_type = "CUVETTE"
                    else:
                        new_type = "SOMMET"

                cursor.updateRow([geom, alt_poly, alt_c, new_type])

                # messages.addMessage(f"Poly ALT_POLY={alt_poly:.2f}, ALT_CENT={alt_c:.2f} => {new_type}")

        # Nettoyage
        if arcpy.Exists(tab_stats):
            arcpy.management.Delete(tab_stats)

        messages.addMessage(f" Résultats sauvegardés dans {sortie_cuvettes}")

class JonctionCourbes(object):
    def __init__(self):
        self.label = "Jonction des courbes de niveau"
        self.description = "Fusionne et intègre les courbes de niveau par altitude."
        self.canRunInBackground = False

    def getParameterInfo(self):
        params = []

        # Paramètre 0 : Liste des couches
        param_layers = arcpy.Parameter(
            displayName="Couches de courbes à traiter",
            name="layers",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
            multiValue=True)
        params.append(param_layers)

        # Paramètre 1 : Champ d'altitude (GPString avec liste déroulante alimentée ensuite)
        param_alt_field = arcpy.Parameter(
            displayName="Champ d'altitude",
            name="alt_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param_alt_field.filter.type = "ValueList"  # liste déroulante
        params.append(param_alt_field)

        # Paramètre 2 : Classe de sortie
        param_output = arcpy.Parameter(
            displayName="Classe d'entités de sortie",
            name="out_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")
        params.append(param_output)

        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        if parameters[0].altered and not parameters[1].altered:
            try:
                first_layer = parameters[0].values[0]
                fields = arcpy.ListFields(first_layer)
                valid_fields = []
                for f in fields:
                    if f.type in ["SmallInteger", "Integer", "Double", "Single", "Float"]:
                        valid_fields.append(f.name)
                parameters[1].filter.list = valid_fields
            except Exception as e:
                arcpy.AddWarning(f"Impossible de lire les champs : {e}")
        return

    def execute(self, parameters, messages):
        layers = parameters[0].values
        alt_field = parameters[1].valueAsText
        out_fc = parameters[2].valueAsText

        arcpy.env.overwriteOutput = True
        merged_fc = "in_memory/merged_fc"

        messages.addMessage("Fusion des couches...")
        arcpy.management.Merge(layers, merged_fc)

        altitudes = sorted({row[0] for row in arcpy.da.SearchCursor(merged_fc, [alt_field])})
        messages.addMessage(f"{len(altitudes)} altitudes détectées.")

        # Créer la classe de sortie avec le même schéma
        desc = arcpy.Describe(layers[0])
        spatial_ref = desc.spatialReference
        arcpy.management.CreateFeatureclass(os.path.dirname(out_fc), os.path.basename(out_fc),
                                             "POLYLINE", template=layers[0], spatial_reference=spatial_ref)

        for alt in altitudes:
            messages.addMessage(f"Traitement de l'altitude {alt} m...")
            alt_clean = re.sub(r'\W+', '_', str(alt))
            temp_layer = f"in_memory/temp_{alt_clean}"

            where_clause = f"{arcpy.AddFieldDelimiters(merged_fc, alt_field)} = {alt}"
            arcpy.management.MakeFeatureLayer(merged_fc, "alt_sel", where_clause)
            arcpy.management.CopyFeatures("alt_sel", temp_layer)
            arcpy.management.Integrate([[temp_layer, ""]], "0.2 Meters")
            arcpy.management.Append(temp_layer, out_fc, "NO_TEST")

        arcpy.management.Delete("in_memory")
        messages.addMessage("Traitement terminé.")
