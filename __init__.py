# encoding: utf-8
#-----------------------------------------------------------
# Copyright (C) 2025 Thomas Baumann
# based on qgis-minimal-plugin from Martin Dobias
#-----------------------------------------------------------
# Licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#---------------------------------------------------------------------
from qgis.core import Qgis, QgsTask, QgsVectorLayer, QgsProject, QgsCoordinateReferenceSystem, QgsApplication, QgsMessageLog
from qgis.PyQt.QtWidgets import QAction, QApplication
from qgis.PyQt.QtGui import QIcon
from qgis.utils import iface
# pylint: disable=relative-beyond-top-level
import os, json

def classFactory(iface):
    return MinimalPlugin(iface)


# Store tasks globally to prevent garbage collection
if not hasattr(iface, "my_plugin_tasks"):
    iface.my_plugin_tasks = []


class LoadLayerTask(QgsTask):
    def __init__(self, description, layer_source, layer_name, provider):
        super().__init__(description, QgsTask.CanCancel)
        self.layer_source = layer_source
        self.layer_name = layer_name
        self.provider = provider
        self.layer = None

    def run(self):
        QgsMessageLog.logMessage("Task started", "MyPlugin", Qgis.Info)
        self.layer = QgsVectorLayer(self.layer_source, self.layer_name, self.provider)
        if not self.layer.isValid():
            QgsMessageLog.logMessage("Layer is invalid", "MyPlugin", Qgis.Critical)
            return False
        QgsMessageLog.logMessage("Layer is valid", "MyPlugin", Qgis.Info)
        return True

    def finished(self, result):
        QgsMessageLog.logMessage(f"Task finished with result: {result}", "MyPlugin", Qgis.Info)
        if result and self.layer:
            
            try:
                #crs = gsLayer.crs()
                #crs.createFromId(25832)
                
                self.layer.setCrs(QgsCoordinateReferenceSystem(25832, QgsCoordinateReferenceSystem.EpsgCrsId))
                QgsProject.instance().addMapLayer(self.layer)
                canvas = iface.mapCanvas()
                canvas.waitWhileRendering()  # modification here
                extent = gsLayer.extent()
                canvas.setExtent(extent)
                canvas.refresh()
            except Exception as e:
                print(e)
                iface.messageBar().pushSuccess("Layer Loaded", f"Layer '{self.layer_name}' loaded successfully.")
        else:
            iface.messageBar().pushCritical("Layer Load Failed", f"Failed to load layer '{self.layer_name}'.")



class MinimalPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

    def initGui(self):
        self.action =  QAction(QIcon(os.path.join(self.plugin_dir,"icon.svg")),"gS-Layer 2 QGIS", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):
        self.clipboard = QApplication.clipboard()
        self.GsLayerConfig = self.clipboard.text()
        print(self.GsLayerConfig)
        plugin_dir = os.path.dirname(__file__)

        geomtype_matcher={'polygon':'MultiPolygon', 'line':'MultiLinestring', 'point':'MultiPoint'}

        print(type(self.GsLayerConfig))
        
        print("GsLayerConfig: {}".format(self.GsLayerConfig))
                

        try:
            d = json.loads(self.GsLayerConfig)
        except json.JSONDecodeError:
            iface.messageBar().pushCritical("Clipboard Error", "Clipboard content is not valid JSON.")
            d = None  # Optional: handle the failure case
            return

        print(d)
        
        try:
            name = d["name"]
        except:
            print("problem bei name")   

        try:
            connectiontype = d["connectiontype"]
        except:
            print("Problem bei connectiontype")
          
        try:
            geomtype=geomtype_matcher[d["geom_type"]]
            
        except:
            print("problem bei geomtype")
            
        if connectiontype=='oraclespatial':
            host = 'piracle'
            try:
                sql = (d["origin"].split("USING UNIQUE ")[0].split("geom FROM (")[1] )
            except:
                print("problem bei sql")

            try:
                user=d["connection"].split('@')[0].split('/')[0]
            except:
                print("problem bei user")

            try:
                pk_column = (d["origin"].split("USING UNIQUE ")[1].split(" ")[0].upper())
            except:
                print("Problem bei PK")                
            
            try:
                pw=d["connection"].split('@')[0].split('/')[1]
            except:
                print("problem bei pw")
                
            try:
                bracket_found=0
                while bracket_found==0:
                    if sql[-1] ==')':
                        bracket_found=1
                    sql = sql[:-1]
                source = 'dbname=\'rd29pdb\' host={} port=1521 user=\'{}\' password=\'{}\' key=\'{}\' srid=25832 type={} table="({})" (GEOM)'.format(host,user,pw,pk_column,geomtype,sql)
                
                #gsLayer = QgsVectorLayer(source, "{}".format(name),  "oracle")
                task = LoadLayerTask("Loading Layer", source, name, "oracle")
                
                iface.my_plugin_tasks.append(task)# Keep reference
                
                #QgsApplication.taskManager().addTask(task)
                success = QgsApplication.taskManager().addTask(task)
                print("Task added:", success)

                    
            except Exception as e:
                print(e)
        elif connectiontype=='shapefile':
            shapepath = os.path.abspath(d["origin"].replace(r'/home/rduser/data/geoservice_data',r'\\vsrv-p-filux.regiodata.local\data\geoservice_data'))
            gsLayer = QgsVectorLayer(shapepath, "{}".format(name),  "ogr")
            try:
                QgsProject.instance().addMapLayer(gsLayer)
            except Exception as e:
                print(e)
            
        #elif connectiontype=='postgis':
        ## dbname, host, port, user, pkey, type, table, type?
        #source = 'dbname={} host={} port={} user={} key={} estimatedmetadata=true srid=25832 type={} checkPrimaryKeyUnicity=\'0\' table={} (line)'format(dbname, host,port, user,pw,pk_column,geomtype,sql)
        #gsLayer = QgsVectorLayer(source, "{}".format(name),  "oracle")


        return True
