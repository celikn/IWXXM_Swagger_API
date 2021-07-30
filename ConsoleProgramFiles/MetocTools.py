
#!/usr/bin/env python3
##################################################
# This tool provides funtionalities;
#       To convert a user given METAR string to IWXXM format XML file.
#       To modify an existing XML document in IWXXM format and, add ColorState and CrossWindAlert
# with “iwxxm-nato” XML elements under remarks by providing a file given in a URL or a direct path. 
#       Additionally, it can search multiple hourly message files to find the recent message of the user
# given station designator for all METAR string within each bulletin file (SAXXXX), with the optional parameter
# to generate an IWXXM format XML file. (not applicable with the web service application)
##################################################
# Author: Naime Celik
# Last Modified: 2021/05/20
##################################################
# use "python MetocTools.py –h"  to list options
##################################################

import getopt
import sys
import subprocess
import pkgutil
import os
import sys
import requests
import matplotlib.pyplot as plt
import json
import avwx
import numpy as np
import math
import folium
from folium import plugins
import pandas as pd
import geopandas
from shapely.geometry import MultiLineString, LineString, Point, mapping
import re
import operator
import timeit
from lxml import etree
import requests
# This part convert metarString to IWXXM format by using
import time
import os
import re
import xml.etree.ElementTree as ET
import pandas as pd
try:
    # pickle was replaced due to error during the aerodrom.db dump() process.
    import pickle5 as pickle
except:
    import pickle
import logging


# Reads token to access avxm rest api from config file.
f = open("config.txt", "r")
AVWX_TOKEN = f.readline().split(":")[1]


# Helper function to get xml root node form url or path
def getXmlRootNode(url, sourceType, createFile=True, outFileName=None):
    """ 
      ================================

      Returns XML node from given file or url 

      ================================
    """

    import time

    if sourceType == "url":

        # Source:https://stackoverflow.com/questions/37889910/how-to-pretty-print-xml-returned-from-requests-lib-in-python

        # http://schemas.wmo.int/iwxxm/

        # Url from us national weather service (The National Weather Service (NWS))

        ##url = "https://nws.weather.gov/schemas/iwxxm-us/3.0/examples/metars/KABQ-152126Z.xml"

        r = requests.get(url, stream=True)

        # LXML

        parser = etree.XMLParser(recover=True)

        xmlRootNode = etree.fromstring(r.content, parser)

        xmlstr = etree.tostring(
            xmlRootNode, xml_declaration=True, encoding="UTF-8", pretty_print=True)

        # print(xmlstr)

        if "METAR" not in xmlRootNode.tag.upper():  # Error handling for XML not containing METAR TAG
            print('Error: XML File does not contain METAR element')
        else:

            timestr = time.strftime("%Y%m%d-%H%M%S")

            if createFile:

                if outFileName == None:
                    fileName = "OriginalXMLFile"+"_"+timestr+".xml"
                else:
                    fileName = outFileName+"_"+timestr+".xml"

                with open(fileName, 'wb') as f:

                    f.write(etree.tostring(xmlRootNode, pretty_print=True))

                # To make sure file is created to further
                time_to_wait = 10
                time_counter = 0
                while not os.path.exists(fileName):
                    time.sleep(1)
                    time_counter += 1
                    if time_counter > time_to_wait:
                        break
                # --------------------------------------------------

                return xmlRootNode, fileName

            else:

                return xmlRootNode, None

    if sourceType == "filePath":

        try:
            with open(url) as f:

                xml = f.read().replace('&', '&amp;')

                xmlRootNode = etree.fromstring(xml)

                xmlstr = etree.tostring(
                    xmlRootNode, xml_declaration=True, encoding="UTF-8", pretty_print=True)

                # print(xmlstr)

                if "METAR" not in xmlRootNode.tag.upper():  # Error handling for XML not containing METAR TAG
                    print('Error: XML File does not contain METAR element')
                else:

                    import time

                    timestr = time.strftime("%Y%m%d-%H%M%S")

                    if createFile:

                        if outFileName == None:
                            fileName = "OriginalXMLFile"+"_"+timestr+".xml"
                        else:
                            fileName = outFileName+"_"+timestr+".xml"

                        with open(fileName, 'wb') as f:

                            f.write(etree.tostring(
                                xmlRootNode, pretty_print=True))

                        # To make sure file is created to further
                        time_to_wait = 10
                        time_counter = 0
                        while not os.path.exists(fileName):
                            time.sleep(1)
                            time_counter += 1
                            if time_counter > time_to_wait:
                                break
                        # --------------------------------------------------

                        return xmlRootNode, fileName

                    else:

                        return xmlRootNode, None

        except IOError:

            print('Error: XML File Not found check the path')

            return None


def retriveMETARsforStationfromListofFiles(stationDesignator, folderPathforFilles):
    """ 
     ================================

     Retrieves Most Recent Metars String inside files

     ================================
    """

    listOfFindMETARs = []

    list_files = [x for x in os.listdir(folderPathforFilles) if x[0] != '.']

    starttime = timeit.default_timer()

    for idx, item in enumerate(list_files):

        file = open(folderPathforFilles + "/"+item, "r")

        for idx, line in enumerate(file):

            metarLineStarts = re.findall(
                r"^(METAR|SPECI) (COR |AUTO )?(?P<station>[A-Z0-9]{4})\s+", line)

            if metarLineStarts != [] and metarLineStarts[0][2] == stationDesignator:

                metarTac = avwx.Metar.from_report(line.strip())

                listOfFindMETARs.append(
                    {"fileName": item, "raw": line, "station": metarLineStarts[0][2], "parsedMetar": metarTac.data, "time": metarTac.data.time.dt})

    #print("The time difference is :", timeit.default_timer() - starttime)

    sortedListOfFindMETARs = sorted(
        listOfFindMETARs, key=operator.itemgetter('time'), reverse=True)

    selectedMostUpdatedMetar = sortedListOfFindMETARs[0]

    return sortedListOfFindMETARs, selectedMostUpdatedMetar


# This function returns current METAR information as JSON response from avwx API for given ICAO station designator

def getMetarInfo(stationDesignator):

    avwxToken = AVWX_TOKEN

    url = 'https://avwx.rest/api/metar/'+stationDesignator

    head = {'Authorization': 'token {}'.format(avwxToken)}

    rM = requests.get(url, headers=head)

    jsonResponseMetar = rM.json()

    return jsonResponseMetar


# This function returns station information as JSON response from avwx API for given ICAO station designator

def getStationInfo(stationDesignator):

    avwxToken = AVWX_TOKEN
    # GetStatioInfoForXMLStation

    url = 'https://avwx.rest/api/station/'+stationDesignator

    head = {'Authorization': 'token {}'.format(avwxToken)}

    r = requests.get(url, headers=head)

    jsonResponseStation = r.json()

    return jsonResponseStation


# This function returns station information as JSON response from avwx API for given ICAO station designator and save it as json

def writeStationInfoIntoFile(jsonResponseStation, pathToSave):

    filePath = pathToSave

    fileName = os.path.split(pathToSave)[-1]

    with open(filePath, 'w') as outFile:

        json.dump(jsonResponseStation, outFile)

    return fileName, filePath


def getStationInfofromFile(filePath):

    try:

        with open(filePath, 'r') as json_file:

            data = json.load(json_file)

            return data

    except IOError:

        print('Station JSON File Not found')

        return None


class CrossWind:

    """

    ================================

    The CrossWind class calculates crosswind components

    ================================

    1. With METAR String:

    ##-------------------------------- Test with Metar String --------------------------------------

    stationDesignator="LICZ"

    metarRawString="METAR "+ stationDesignator+" 011350Z 04005KT 300V080 9999 SCT040 BKN090 15/10 Q1011"

    jsonResponseStation=getStationInfo(stationDesignator)

    crosswindforStation= CrossWind(metarRawString,jsonResponseStation,metarFormatType="raw_String")

    ##-------------------------------- Test with avwx_JSON ---------------------------------------

    jsonResponseMetar=getMetarInfo(stationDesignator)

    print(jsonResponseMetar)

    crosswindforStation = CrossWind(jsonResponseMetar,jsonResponseStation,metarFormatType="avwx_JSON")

    ##-------------------------------- Test with Provided XML Root ---------------------------------------

    url="http://www.meteocenter.ru/iwxxm/xml/A_LARU20UAKK130830_C_RUMS_20210413084323.xml" ### Some xml with CAVOK 

    xmlRootNodeforMETAR,fileName=getXmlRootNode(url,"url",createFile=True)  ##

    ##xmlRootNodeforMETAR,fileName=getXmlRootNode(url,"filePath",createFile=False) ### to access xml file from local path 

    crosswindforStation= CrossWind(xmlRootNodeforMETAR,jsonResponseStation,metarFormatType="XML")

    ##-------------------------------- Calculation of CrossWind --------------------------------------    

    crosswindComponentForStation=crosswindforStation.calculateCrossWindComponent()

    print (crosswindforStation)



    ## Calculate Map Properties for CrossWind and Display on the Map

    runwayGDF=crosswindforStation.getRunwayLineGeodataFrame()

    windGDF=crosswindforStation.getWindDirectionGedataFrame()

    crosswindforStation.displayMap()

    """

    def __init__(self, responseMetar, jsonResponseStation, metarFormatType="avwx_JSON"):

        self.metarFormatType = metarFormatType

        self.responseMetar = responseMetar

        self.jsonResponseStation = jsonResponseStation

    def __str__(self):

        crossWindComponentItemPrintList = []

        if self.crossWindComponentItems:

            crossWindComponentItemPrintList.append(
                f'____________________________________')

            for idx, item in enumerate(self.crossWindComponentItems):

                windSpeed, windDirection, runwayDirection, angleBetweenRunwayAndWind, crossWindComponent, runwayIdent = self.crossWindComponentItems[
                    idx]

                crossWindComponentItemPrintList.append(
                    f'---Runway Index-------:{idx}')

                crossWindComponentItemPrintList.append(
                    f'windSpeed:{windSpeed}')

                crossWindComponentItemPrintList.append(
                    f'windDirection:{windDirection}')

                crossWindComponentItemPrintList.append(
                    f'runwayDirection:{runwayDirection}')

                crossWindComponentItemPrintList.append(
                    f'angleBetweenRunwayAndWind:{angleBetweenRunwayAndWind}')

                crossWindComponentItemPrintList.append(
                    f'crossWindComponent:{crossWindComponent}')

                crossWindComponentItemPrintList.append(
                    f'runwayIdent:{runwayIdent}')

            crossWindComponentItemPrintList.append(
                f'____________________________________')

            return "\n".join(crossWindComponentItemPrintList)

        else:

            return f'CrossWindComponent for {self.responseMetar["station"]} is not available'

    def _getAzimuthAngleDifference(self, b1, b2):

        # Source:  https://rosettacode.org/wiki/Angle_difference_between_two_bearings#Python

        r = (b2 - b1) % 360.0

        # Python modulus has same sign as divisor, which is positive here,

        # so no need to consider negative case

        if r >= 180.0:

            r -= 360.0

        return r

    def createModifiedIwxxmFileforCrossWind(self, nameSpaceKey="iwxxm-nato", nameSpaceUrl="http://shape.nato.int", version="1.0", fileName=None, writeFile=True, readFileContent=None):

        if self.metarFormatType == "XML":

            if fileName != None:

                if readFileContent != None:  # if file content is given then no file opening, this is used for app.py

                    root = readFileContent
                else:

                    with open(fileName) as fobj:

                        xml = fobj.read()

                    root = etree.fromstring(xml)

            else:

                root = self.responseMetar

            #ns_iwxxmnato = "http://shape.nato.int/iwxxm-nato/1.0"

            ns_iwxxmnato = nameSpaceUrl+"/"+nameSpaceKey+"/"+version

            nsmap = root.nsmap

            #nsmap["iwxxm-nato"] = ns_iwxxmnato

            nsmap[nameSpaceKey] = ns_iwxxmnato

            new_root = etree.Element(root.tag, nsmap=nsmap)

            new_root[:] = root[:]

            # Adding remarks element with iwxxm tag if not exists

            # Check if remark element already exist

            remarkExist = False

            for element in new_root.iter():

                if element.getroottree().getpath(element).endswith("remarks"):

                    elementRemarks = element

                    remarkExist = True

            if not remarkExist:

                elementRemarks = etree.Element(
                    '{%s}%s' % (new_root.nsmap["iwxxm"], 'remarks'))

                new_root.append(elementRemarks)

            # Creates and assings INPUT for ColorStates with iwxxm-nato tag

            # elementColorState=etree.Element('{%s}%s' % (ns_iwxxmnato, 'colorState'),

            # description=colorDescription)  ### colorDescription is INPUT

            # Write if the component runway direction is different

            runwayDirectionTemp = None

            for idx, item in enumerate(self.crossWindComponentItems):

                windSpeed, windDirection, runwayDirection, angleBetweenRunwayAndWind, crossWindComponent, runwayIdent = self.crossWindComponentItems[
                    idx]

                if runwayDirectionTemp == None or runwayDirectionTemp != runwayDirection:

                    # Adding simple colorState Element

                    # elementColorState=etree.Element('colorState')  ### without nato namespace

                    elementCrossWind = etree.Element('{%s}%s' % (ns_iwxxmnato, 'crossWindAlert'), runwayDirection=str(
                        runwayDirection) + " deg", runwayIdent=runwayIdent)

                    elementCrossWind.text = str(
                        round(crossWindComponent, 3))  # is INPUT

                    elementRemarks.append(elementCrossWind)

                    runwayDirectionTemp = runwayDirection

            #print (etree.tostring(new_root, pretty_print=True))

            if fileName == None:

                timestr = time.strftime("%Y%m%d-%H%M%S")

                fileName = self.stationDesignator+'_'+timestr+'_modified'+'.xml'

                if writeFile:

                    with open('crossWindAdded_'+fileName, 'wb') as f:

                        f.write(etree.tostring(new_root, pretty_print=True))

                return 'crossWindAdded_'+fileName, new_root

            else:

                if writeFile:

                    with open('crossWindAdded_'+fileName, 'wb') as f:

                        f.write(etree.tostring(new_root, pretty_print=True))

                return 'crossWindAdded_'+fileName, new_root

    def calculateCrossWindComponent(self):

        crossWindComponentItems = []

        # todo: Check if METAR and jsonResponse Station information matches

        if self.metarFormatType == "avwx_JSON":

            # Gets the station designator and wind information from METAR data

            self.stationDesignator = self.responseMetar["station"]

            try:

                windSpeed = self.responseMetar["wind_speed"]["value"]

                windDirection = self.responseMetar["wind_direction"]["value"]

            except:

                windSpeed = None

                windDirection = None

        elif self.metarFormatType == "raw_String":

            metarTac = avwx.Metar.from_report(self.responseMetar)

            self.stationDesignator = metarTac.data.station

            try:

                windDirection = metarTac.data.wind_direction.value

                windSpeed = metarTac.data.wind_speed.value

            except:

                windSpeed = None

                windDirection = None

        elif self.metarFormatType == "XML":

            for element in self.responseMetar.iter():

                if element.getroottree().getpath(element).endswith("designator") or element.getroottree().getpath(element).endswith("locationIndicatorICAO"):

                    self.stationDesignator = element.text

                if element.getroottree().getpath(element).endswith("meanWindDirection"):

                    windDirection = int(element.text)

                if element.getroottree().getpath(element).endswith("meanWindSpeed"):

                    windSpeed = int(element.text)

        # Exception for checking runway information

        try:

            stationRunways = self.jsonResponseStation["runways"]

        except:

            # In this case station does not have runway information to calculate crosswind component

            return None

        print(self.responseMetar)

        print(self.jsonResponseStation)

        if stationRunways != None:

            for idx, runway in enumerate(stationRunways):

                if windDirection != None:

                    ##print (runway["ident1"])

                    # print (round(runway["bearing1"]/10)*10)  ### To more precise, we can use the actual bearing directly

                    runwayDirection1 = round(runway["bearing1"]/10)*10

                    # Considering situation 359 wind direction, 56 236 as runway direction

                    # It has to consider azimuth angle difference

                    # angleBetweenRunwayAndWind1=max(windDirection-runwayDirection1,runwayDirection1-windDirection)  ### need to be positive angle value

                    angleBetweenRunwayAndWind1 = max(self._getAzimuthAngleDifference(windDirection, runwayDirection1), self._getAzimuthAngleDifference(
                        runwayDirection1, windDirection))  # need to be positive angle value

                    runwayDirection2 = round(runway["bearing2"]/10)*10

                    # angleBetweenRunwayAndWind2=max(windDirection-runwayDirection2,runwayDirection2-windDirection)  ### need to be positive angle value

                    angleBetweenRunwayAndWind2 = max(self._getAzimuthAngleDifference(windDirection, runwayDirection2), self._getAzimuthAngleDifference(
                        runwayDirection2, windDirection))  # need to be positive angle value

                    runwayDirections = [runwayDirection1, runwayDirection2]

                    runwayIdents = [runway["ident1"], runway["ident2"]]

                    anglesBetweenRunwayAndWind = [
                        angleBetweenRunwayAndWind1, angleBetweenRunwayAndWind2]

                    # We are getting the index of the angle which is smaller than 100

                    # with the 10 rounding some result with 100 degree normally 90
                    idxForRunway = np.where(
                        np.array(anglesBetweenRunwayAndWind) <= 100)[0][0]

                    # And final calculation for the crosswindcomponent with the selected angle

                    # Crosswind speed = wind speed * sin ( Î± )

                    crossWindComponent = windSpeed * \
                        math.sin(math.radians(
                            anglesBetweenRunwayAndWind[idxForRunway]))

                    runwayIdent = runwayIdents[idxForRunway]

                    crossWindComponentItems.append([windSpeed, windDirection, runwayDirections[idxForRunway],
                                                   anglesBetweenRunwayAndWind[idxForRunway], crossWindComponent, runwayIdent])

                else:

                    print("wind speed or wind direction is None")

                    crossWindComponentItems.append(
                        [windSpeed, windDirection, None, None, None, None])

            self.crossWindComponentItems = crossWindComponentItems

            return self.crossWindComponentItems

    # This part is to calculate geometry to draw runway direction and wind direction on folium map

    # Get runway and wind direction geometry

    def _getRunwayPoint(self, pt, bearing, dist):

        bearing = math.radians(bearing)

        x = pt.x + dist * math.sin(bearing)

        y = pt.y + dist * math.cos(bearing)

        return Point(x, y)

    def _getWindDirectionPoint(self, pt, bearing, dist):

        bearing = math.radians(bearing)

        x = pt.x + dist * math.sin(bearing)

        y = pt.y + dist * math.cos(bearing)

        return Point(x, y)

    def getRunwayLineGeodataFrame(self):

        df = pd.json_normalize(self.jsonResponseStation)

        airport_gdf = geopandas.GeoDataFrame(
            df, geometry=geopandas.points_from_xy(df.longitude, df.latitude))

        airport_gdf.head()

        airport_gdf = airport_gdf.set_crs(epsg=4326)

        airport_gdf = airport_gdf.to_crs(epsg=3857)

        # Calculate Runway Line

        x = float(airport_gdf.geometry.x.iloc[0])

        y = float(airport_gdf.geometry.y.iloc[0])

        pt = Point(x, y)

        if self.jsonResponseStation["runways"] != None:

            length_m = int(
                int(self.jsonResponseStation["runways"][0]["length_ft"]) * 0.3048)

            bearing1 = int(self.jsonResponseStation["runways"][0]["bearing1"])

            bearing2 = int(self.jsonResponseStation["runways"][0]["bearing2"])

            ThePt1 = self._getRunwayPoint(pt, bearing1, length_m)

            ThePt2 = self._getRunwayPoint(pt, bearing2, length_m)

            runwayLine = LineString([ThePt1, ThePt2])

            runwayLineGDF = geopandas.GeoDataFrame(geometry=[runwayLine])

            runwayLineGDF = runwayLineGDF.set_crs(epsg=3857)

            runwayLineGDF = runwayLineGDF.to_crs(epsg=4326)

            runwayLineGDF["longitude"] = df.longitude

            runwayLineGDF["latitude"] = df.latitude

            runwayLineGDF["icao"] = df.icao

            runwayLineGDF["name"] = df.name

            self.runwayLineGDF = runwayLineGDF

        else:

            self.runwayLineGDF = None

        return self.runwayLineGDF

        # plot with contextily

        #ax = runwayLineGDF.plot(alpha=0.5, color='r', edgecolor="black", figsize=(16, 16))

        # plt.show()

    def getWindDirectionGedataFrame(self):

        df = pd.json_normalize(self.jsonResponseStation)

        airport_gdf = geopandas.GeoDataFrame(
            df, geometry=geopandas.points_from_xy(df.longitude, df.latitude))

        airport_gdf.head()

        airport_gdf = airport_gdf.set_crs(epsg=4326)

        airport_gdf = airport_gdf.to_crs(epsg=3857)

        x = float(airport_gdf.geometry.x.iloc[0])

        y = float(airport_gdf.geometry.y.iloc[0])

        pt = Point(x, y)

        windSpeed, windDirection, runwayDirection, angleBetweenRunwayAndWind, crossWindComponent, runwayIdent = self.crossWindComponentItems[
            0]

        if windDirection == None:

            # No wind direction the point of the center will be return

            windDirectionLine = Point(pt)

            windDirectionLineGDF = geopandas.GeoDataFrame(
                geometry=[windDirectionLine])

            windDirectionLineGDF["windSpeed"] = None

            windDirectionLineGDF["windDirection"] = None

            windDirectionLineGDF["runwayDirection"] = None

            windDirectionLineGDF["angleBetweenRunwayAndWind"] = None

            windDirectionLineGDF["crossWindComponent"] = None

            windDirectionLineGDF = windDirectionLineGDF.set_crs(epsg=3857)

            windDirectionLineGDF = windDirectionLineGDF.to_crs(epsg=4326)

        else:

            length_m = int(
                int(self.jsonResponseStation["runways"][0]["length_ft"]) * 0.3048/2)

            windBearing = int(windDirection)

            ThePt1 = self._getWindDirectionPoint(pt, windBearing, length_m)

            windDirectionLine = LineString([pt, ThePt1])

            windDirectionLineGDF = geopandas.GeoDataFrame(
                geometry=[windDirectionLine])

            windDirectionLineGDF = windDirectionLineGDF.set_crs(epsg=3857)

            windDirectionLineGDF = windDirectionLineGDF.to_crs(epsg=4326)

            windDirectionLineGDF["windSpeed"] = windSpeed

            windDirectionLineGDF["windDirection"] = windDirection

            windDirectionLineGDF["runwayDirection"] = runwayDirection

            windDirectionLineGDF["angleBetweenRunwayAndWind"] = angleBetweenRunwayAndWind

            windDirectionLineGDF["crossWindComponent"] = round(
                crossWindComponent, 3)

            # plot with contextily

            #ax = windDirectionLineGDF.plot(alpha=0.5, color='r', edgecolor="black", figsize=(16, 16))

            # plt.show()

        self.windDirectionLineGDF = windDirectionLineGDF

        return windDirectionLineGDF

    def displayMap(self):

        print("Drawing the map")

        # Read: https://medium.com/@kumartan1912/spatial-visualization-folium-maps-python-43c3bc150603

        dataRunway = self.runwayLineGDF

        dataWind = self.windDirectionLineGDF

        # Create a folium map object.

        my_map = folium.Map(location=[float(dataRunway['latitude']), float(
            dataRunway['longitude'])], zoom_start=13, height=500)

        # folium.Marker(location=[float(runwayLineGDF['latitude']), float(runwayLineGDF['longitude'])]).add_to(my_map

        for i in range(0, len(dataRunway)):

            folium.Marker(

                location=[dataRunway.iloc[i]['latitude'],
                          dataRunway.iloc[i]['longitude']],

                popup=dataRunway.iloc[i]['name'],

            ).add_to(my_map)

        # folium.GeoJson(runwayLineGeoJson[0]).add_to(my_map)

        # If you use a linestring generate points as below

        #runwayLineX,runwayLineY = runwayLine.coords.xy

        #zippedrunwayLinePoints=list(map(lambda x,y: tuple([y,x]),runwayLineX,runwayLineY))

        #folium.PolyLine(zippedrunwayLinePoints, color="red", weight=2.5, opacity=1).add_to(my_map)

        # folium.GeoJson(runwayLineGDF).add_to(my_map)

        # Source https://stackoverflow.com/questions/35516318/plot-colored-polygons-with-geodataframe-in-folium

        runwayLayer = folium.GeoJson(dataRunway, style_function=lambda feature: {

            'fillColor': "red",

            'color': "black",

            'weight': 3,

            'fillOpacity': 0.5,

        }).add_to(my_map)

        runwayLayer.layer_name = 'Runway Layer'

        windDirectionLayer = folium.GeoJson(dataWind, style_function=lambda feature: {

            'fillColor': "red",

            'color': "red",

            'weight': 3,

            'fillOpacity': 0.5,

        }).add_child(folium.Popup(



            "windSpeed:"+str(dataWind["windSpeed"][0]) + "\n"

            + " windDirection:"+str(dataWind["windDirection"][0])

            + " angleBetweenRunwayAndWind:" +
            str(dataWind["angleBetweenRunwayAndWind"][0])

            + " crossWindComponent:" + str(dataWind["crossWindComponent"][0]))).add_to(my_map)

        windDirectionLayer.layer_name = 'Wind Direction Layer'

        # TODO: add Iframe to the map

        # https://stackoverflow.com/questions/54595931/show-different-pop-ups-for-different-polygons-in-a-geojson-folium-python-ma

        # iterate over GEOJSON, style individual features, and add them to FeatureGroup

        # Add the elevation model to the map object.

        #my_map.add_ee_layer(dem.updateMask(dem.gt(0)), vis_params, 'DEM')

        # Add a layer control panel to the map.

        folium.raster_layers.TileLayer('Open Street Map').add_to(my_map)

        #folium.raster_layers.TileLayer('Stamen Terrain').add_to(my_map)

        #folium.raster_layers.TileLayer('Stamen Toner').add_to(my_map)

        #folium.raster_layers.TileLayer('Stamen Watercolor').add_to(my_map)

        #folium.raster_layers.TileLayer('CartoDB Positron').add_to(my_map)

        #folium.raster_layers.TileLayer('CartoDB Dark_Matter').add_to(my_map)

        my_map.add_child(folium.LayerControl())

        minimap = plugins.MiniMap(toggle_display=True)

        my_map.add_child(minimap)

        # add full screen button to map

        plugins.Fullscreen(position='topright').add_to(my_map)

        draw = plugins.Draw(export=True)

        draw.add_to(my_map)

        # Display the map.

        display(my_map)

        # my_map.save("Crosswindmap.html")


class ColorState:

    """

    ================================

    The ColorState class calculates color state



                            CH = Cloud Height (ft).

                            V = Visibility (m).



    BLU                   CH &gt; 2500  -             V &gt; 8000

    WHT        2500 &gt;= CH &gt; 1500  -  8000 &gt;= V &gt; 5000

    GRN        1500 &gt;= CH &gt; 700   -  5000 &gt;= V &gt; 3700

    YLO1       700 &gt;= CH &gt; 500   -  3700 &gt;= V &gt; 2500

    YLO2       500 &gt;= CH &gt; 300   -  2500 &gt;= V &gt; 1600

    AMB        300 &gt;= CH &gt; 200   -  1600 &gt;= V &gt;  800

    RED        200 &gt;= CH            -   800 &gt;= V



    ================================

    1. With METAR String:

    ##-------------------------------- Test with Metar String --------------------------------------

    stationDesignator="LICZ"

    metarRawString="METAR "+ stationDesignator+" 011350Z 04005KT 300V080 9999 SCT040 BKN090 15/10 Q1011"

    jsonResponseStation=getStationInfo(stationDesignator)

    colorStateforStation= ColorState(metarRawString,metarFormatType="raw_String")

    ##-------------------------------- Test with avwx_JSON ---------------------------------------

    jsonResponseMetar=getMetarInfo(stationDesignator)

    print(jsonResponseMetar)

    colorStateforStation= ColorState(jsonResponseMetar,metarFormatType="avwx_JSON")

    ##-------------------------------- Test with Provided XML Root ---------------------------------------

    url="http://www.meteocenter.ru/iwxxm/xml/A_LARU20UAKK130830_C_RUMS_20210413084323.xml" ### Some xml with CAVOK 

    xmlRootNodeforMETAR,fileName=getXmlRootNode(url,"url",createFile=True)  ##

    ##xmlRootNodeforMETAR,fileName=getXmlRootNode(url,"filePath",createFile=False) ### to access xml file from local path 

    colorStateforStation= ColorState(xmlRootNodeforMETAR,metarFormatType="XML")

    ##-------------------------------- Calculation of ColorState --------------------------------------    

    ## Calculate ColorState

    colorStateforStation= ColorState(xmlRootNodeforMETAR,metarFormatType="XML")

    colorStateforStation.calculateColorState()

    print(colorStateforStation)

    """

    def __init__(self, responseMetar, metarFormatType="avwx_JSON"):

        self.metarFormatType = metarFormatType

        self.responseMetar = responseMetar

    def __str__(self):

        if self.colorState:

            return f"Calculated Color State: {self.colorState}"

        else:

            return f"Color State has not been calculated"

    def createModifiedIwxxmFileforColorState(self, nameSpaceKey="iwxxm-nato", nameSpaceUrl="http://shape.nato.int", version="1.0", fileName=None, writeFile=True, readFileContent=None):

        if self.metarFormatType == "XML":

            if fileName != None:

                if readFileContent != None:

                    # if file content is given then no file opening, this is used for app.py
                    root = readFileContent
                else:

                    with open(fileName) as fobj:

                        xml = fobj.read()

                    root = etree.fromstring(xml)

            else:

                root = self.responseMetar

            #ns_iwxxmnato = "http://shape.nato.int/iwxxm-nato/1.0"

            ns_iwxxmnato = nameSpaceUrl+"/"+nameSpaceKey+"/"+version

            nsmap = root.nsmap

            #nsmap["iwxxm-nato"] = ns_iwxxmnato

            nsmap[nameSpaceKey] = ns_iwxxmnato

            new_root = etree.Element(root.tag, nsmap=nsmap)

            new_root[:] = root[:]

            # Adding remarks element with iwxxm tag if not exists

            # Check if remark element already exist

            remarkExist = False

            for element in new_root.iter():

                if element.getroottree().getpath(element).endswith("remarks"):

                    elementRemarks = element

                    remarkExist = True

            if not remarkExist:

                elementRemarks = etree.Element(
                    '{%s}%s' % (new_root.nsmap["iwxxm"], 'remarks'))

                new_root.append(elementRemarks)

            # Creates and assings INPUT for ColorStates with iwxxm-nato tag

            # elementColorState=etree.Element('{%s}%s' % (ns_iwxxmnato, 'colorState'),

            # description=colorDescription)  ### colorDescription is INPUT

            # Adding simple colorState Element

            # elementColorState=etree.Element('colorState')  ### without nato namespace

            elementColorState = etree.Element(
                '{%s}%s' % (ns_iwxxmnato, 'colorState'))

            elementColorState.text = self.colorState  # sampleAssingedColor is INPUT

            elementRemarks.append(elementColorState)

            print(etree.tostring(new_root, pretty_print=True))

            # createModifiedIwxxmFileforColorState(modifiedFile,colorState)

            if fileName == None:

                timestr = time.strftime("%Y%m%d-%H%M%S")

                fileName = stationDesignator+'_'+timestr+'_modified'+'.xml'

                if writeFile:

                    with open('colorStateAdded_'+fileName, 'wb') as f:

                        f.write(etree.tostring(new_root, pretty_print=True))

                return 'colorStateAdded_'+fileName, new_root

            else:

                if writeFile:

                    with open('colorStateAdded_'+fileName, 'wb') as f:

                        f.write(etree.tostring(new_root, pretty_print=True))

                return 'colorStateAdded_'+fileName, new_root

    def _assignColorState(self, visibility, baseOfCloudHeigh=0):

        if visibility >= 8000 or baseOfCloudHeigh >= 2500:  # "BLU":"CH &gt; 2500  -  V &gt; 8000"

            assignColor = "BLU"

        elif (visibility < 8000 and visibility >= 5000) or (baseOfCloudHeigh < 2500 and baseOfCloudHeigh >= 1500):

            assignColor = "WHT"

        elif (visibility < 5000 and visibility >= 3700) or (baseOfCloudHeigh < 1500 and baseOfCloudHeigh >= 700):

            assignColor = "GRN"

        elif (visibility < 3700 and visibility >= 2500) or (baseOfCloudHeigh < 700 and baseOfCloudHeigh >= 500):

            assignColor = "YLO1"

        elif (visibility < 2500 and visibility >= 1600) or (baseOfCloudHeigh < 500 and baseOfCloudHeigh >= 300):

            assignColor = "YLO2"

        elif (visibility < 1600 and visibility >= 800) or (baseOfCloudHeigh < 300 and baseOfCloudHeigh >= 200):

            assignColor = "AMB"

        elif visibility < 800 or baseOfCloudHeigh < 200:

            assignColor = "RED"

        return assignColor

    def _getBaseOfCloudHeigh_on_SCT_BKN_OVC(self, valueCloudAmountList, valueCloudBaseList):

        try:

            exist_SCT_BKN_OVC = {idx: valueCloudAmount for idx, valueCloudAmount in enumerate(valueCloudAmountList) if (
                "SCT" in valueCloudAmount) or ("BKN" in valueCloudAmount) or ("OVC" in valueCloudAmount)}

            ##print (len(exist_SCT_BKN_OVC))

            # index of the cloud layer to use smallest of the broken or overcast
            idxCL = list(exist_SCT_BKN_OVC.keys())[0]

            baseOfCloudHeigh = valueCloudBaseList[idxCL]

        except:

            print("baseOfCloudHeigh:None")

            baseOfCloudHeigh = None

        return baseOfCloudHeigh

    def calculateColorState(self):

        valueCloudBaseList = []

        valueCloudAmountList = []

        valueVisibilityList = []

        cavok = False

        if self.metarFormatType == "raw_String":

            # originalDecodedTac=Metar.Metar(self.originalTac)

            #print (originalDecodedTac.visibility())

            metarTac = avwx.Metar.from_report(self.responseMetar)

            print(metarTac)

            print(metarTac.data)

            for item in metarTac.data.clouds:

                valueCloudAmountList.append(item.type)

                valueCloudBaseList.append(item.base*100)

            valueVisibilityList.append(metarTac.data.visibility.value)

            if "CAVOK" in metarTac.data.raw:

                cavok = True

        elif self.metarFormatType == "avwx_JSON":

            for item in self.responseMetar["clouds"]:

                print(item)

                valueCloudAmountList.append(item["type"])

                valueCloudBaseList.append(int(item["altitude"])*100)

            valueVisibilityList.append(
                self.responseMetar["visibility"]["value"])

            if "CAVOK" in self.responseMetar["raw"]:

                cavok = True

        elif self.metarFormatType == "XML":

            for element in self.responseMetar.iter():

                if "cloud" in element.getroottree().getpath(element):

                    if "CloudLayer" in element.getroottree().getpath(element):

                        if "base" in element.getroottree().getpath(element):

                            #print (element.text)

                            valueCloudBaseList.append(int(element.text))

                if "amount" in element.getroottree().getpath(element):

                    #print (element.attrib)

                    valueCloudAmountList.append(
                        element.attrib.values()[0].split("/")[-1])

            for element in self.responseMetar.iter():

                if "visibility" in element.getroottree().getpath(element):

                    if element.getroottree().getpath(element).endswith("prevailingVisibility"):

                        valueVisibilityList.append(int(element.text))

                        #print (element.text, element.tag,element.attrib)

                        # TODO: if the visibility is not in m need conversion to meter

                    if element.getroottree().getpath(element).endswith("prevailingVisibilityOperator"):

                        valueVisibilityList.append(element.text)

                        #print (element.text, element.tag,element.attrib)

                if "MeteorologicalAerodromeObservationRecord" in element.getroottree().getpath(element):

                    if "cloudAndVisibilityOK" in element.attrib:

                        if element.attrib["cloudAndVisibilityOK"] == "true" or element.attrib["cloudAndVisibilityOK"] == True:

                            cavok = True

        # Now calculate the colorState

        # print(valueCloudAmountList)

        # Condition1: No Cloud Layer data
        if len(valueVisibilityList) != 0 and len(valueCloudBaseList) == 0:

            # In this case no cloud height in the data, so only visibility will be take into account

            baseOfCloudHeigh = 0

            visibility = valueVisibilityList[0]

            assignColor = self._assignColorState(visibility, baseOfCloudHeigh)

        # Condition2: No Visibility data
        elif len(valueVisibilityList) == 0 and len(valueCloudBaseList) != 0:

            # In this case no visibility in the data, so only cloud height will be take into account

            visibility = 0

            baseOfCloudHeigh = self._getBaseOfCloudHeigh_on_SCT_BKN_OVC(
                valueCloudAmountList, valueCloudBaseList)

            if baseOfCloudHeigh == None:

                assignColor = "BLU"

            else:

                assignColor = self._assignColorState(
                    visibility, baseOfCloudHeigh)

        # Condition3: Both Cloud Layer and Visibility available
        elif len(valueVisibilityList) != 0 and len(valueCloudBaseList) != 0:

            baseOfCloudHeigh = self._getBaseOfCloudHeigh_on_SCT_BKN_OVC(
                valueCloudAmountList, valueCloudBaseList)

            visibility = valueVisibilityList[0]

            if baseOfCloudHeigh == None:

                assignColor = "BLU"

            else:

                assignColor = self._assignColorState(
                    visibility, baseOfCloudHeigh)

        elif len(valueVisibilityList) == 0 and len(valueCloudBaseList) == 0:

            assignColor = None

        print("VisibilityList:", valueVisibilityList)

        print("CloudBaseList:", valueCloudBaseList)

        print("CloudAmountList:", valueCloudAmountList)

        # If data contains CAVOK colorstate will be assigned to BLU

        if cavok == True:

            self.colorState = "BLU"

        else:

            self.colorState = assignColor


class Metar2XML:

    def __init__(self, stationDesignator, METAR_String):

        self.stationDesignator = stationDesignator

        self.METAR_String = METAR_String

    def _module_exists(self, module_name):

        return module_name in (name for loader, name, ispkg in pkgutil.iter_modules())

    def _installGIFTs(self):

        startingDirectory = os.getcwd()

        print(startingDirectory)

        subprocess.run(["git", "clone", "https://github.com/NOAA-MDL/GIFTs.git"],
                       check=True, stdout=subprocess.PIPE).stdout

        #subprocess.run(["git", "clone", "https://github.com/NOAA-MDL/GIFTs.git"], check=True, stdout=subprocess.PIPE).stdout

        os.chdir('GIFTs')

        GIFTsDirectory = os.getcwd()

        #lsResult = subprocess.check_output(['ls'])

        # print(lsResult)

        subprocess.check_call(
            [sys.executable, "setup.py", "install", "--prefix=/usr/local"])

        os.chdir(startingDirectory)

        return GIFTsDirectory

    def createAirportTableforGIFTs(self, airpotDataUrl='http://ourairports.com/data/airports.csv', filePathforFile='./aerodromes.tbl'):

        df = pd.read_csv(airpotDataUrl)

        df.head()

        # print(df['ident'].to_string())

        ndf = pd.DataFrame()

        ndf['ICAO'] = df['ident']

        ndf['IATA'] = ""

        ndf['AltID'] = ""

        ndf['FullName'] = ""  # The name removed

        ndf["Latitude"] = df["latitude_deg"]

        ndf["Longitude"] = df["longitude_deg"]

        ndf["Elevation"] = 0

        # Field #1 = ICAO identifier - 4 characters (required)

        # Field #2 = IATA identifier - 3 characters (optional)

        # Field #3 = Alternate identifier 3-6 characters (optional)

        # Field #4 = Full name of aerodrome, up to 60 characters (optional)

        # Field #5 = Latitude of aerodrome in degrees (decimal)  (southern latitudes are negative) (required)

        # Field #6 = Longitude of aerodrome in degrees (decimal) (western longitudes are negative) (required)

        # Field #7 = Elevation of aerodrome in metres (required)

        ndf.head()

        pd.options.display.float_format = '{:.6f}'.format

        x = ndf.to_string(header=False,

                          index=False,

                          index_names=False).split('\n')

        vals = ['|'.join(ele.split()) for ele in x]

        # print(vals)

        with open(filePathforFile, 'w') as f:

            f.write(

                ndf.to_csv(sep="|", index=False, header=False)
            )

        print("aerodromes.tbl has been created!")

        return filePathforFile

    def createAerodromesDBforGIFTs(self, filePathforFile='./aerodromes.tbl'):

        database = {}

        with open(filePathforFile) as _fh:

            for lne in _fh:

                if lne.startswith('#'):

                    continue

                try:

                    sid, IATAId, alternateId, name, lat, lon, elev = lne.split(
                        '|')

                except ValueError:

                    continue

                if len(sid) == 4 and sid.isalpha():

                    database[sid] = '%s|%s|%s|%.5f %.5f %d' % (name[:60].strip().upper(), IATAId[:3].strip().upper(),

                                                               alternateId[:6].strip().upper(), float(
                                                                   lat), float(lon),

                                                               int(elev))

                    print(lne)

        with open('./aerodromes2.db', 'wb') as _fh:

            pickle.dump(database, _fh, protocol=pickle.HIGHEST_PROTOCOL)

        #subprocess.call('cp ' +'./aerodromes2.db'+' ./GIFTs/demo/aerodromes2.db', shell=True)

        print("aerodromes2.tbl has been created!")

        # read data from a file

        # with open('/content/aerodromes.db') as fin:

        #   print(pickle.load(fin))

    def checkGIFTsModule_convertMETARstring2IWXXM(self, aerodromesDBPath="aerodromes2.db", writeFile=True):
        stationDesignator = self.stationDesignator
        METAR_String = self.METAR_String
        print("Processing ", stationDesignator, METAR_String)

        if self._module_exists("gifts"):
            import gifts

            print(
                "...Gift Module exist, it will check for aerodromes.tbl and aerodromes.db ")
            print(" ")
            if os.path.isfile(aerodromesDBPath) != True:
                print("...Creating aerodromes.tbl and aerodromes.db ")
                self.createAirportTableforGIFTs(
                    airpotDataUrl='http://ourairports.com/data/airports.csv', filePathforFile='./aerodromes.tbl')
                self.createAerodromesDBforGIFTs(
                    filePathforFile='./aerodromes.tbl')
                print(" ")

            else:
                print("...Existing aerodromes.tbl and aerodromes.db ")
                print(" ")

            # startingDirectory=os.getcwd()

            if not METAR_String.endswith("="):

                METAR_String += "="

            if not METAR_String.startswith("METAR "):

                if stationDesignator not in METAR_String:
                    METAR_String = stationDesignator+" "+METAR_String

                METAR_String = "METAR "+METAR_String

            # To able to get coordinates of the airport loading db file with pickle

            with open(aerodromesDBPath, 'rb') as _fh:

                aerodromes = pickle.load(_fh)

            # By using Regular expressions to identify TAC file contents based on WMO AHL line

            encoders = []

            encoders.append((re.compile(r'^S(A|P)[A-Z][A-Z]\d\d\s+[A-Z]{4}\s+\d{6}', re.MULTILINE),

                             gifts.METAR.Encoder(aerodromes)))

            #print (encoders)

            logger = logging.getLogger()

            # created tac with abstract SA indicator SA code required by the regular expresion that defined by gift module

            abstractTacText = """SAXX00 """+stationDesignator + \
                """ 000000""" + """\n"""+METAR_String

            # Checks airport db until it founds the station designator

            for regexp, encoder in encoders:

                result = regexp.search(abstractTacText)

                if result is not None:

                    break

            # print(abstractTacText)

            bulletin = encoder.encode(abstractTacText[result.start():])

            for xml in bulletin:

                tree = ET.XML(ET.tostring(xml))

                # print(tree)

                icaoID = tree.find(
                    './/*{http://www.aixm.aero/schema/5.1.1}locationIndicatorICAO')

                #print (icaoID.text)

                if icaoID.text is not None:

                    msg = '%s: SUCCESS' % icaoID.text

                    logger.info(msg)

                else:

                    logger.info('IWXXM Advisory created!')

            # Write the Meteorological Bulletin containing IWXXM documents in the same directory
            #bulletinIdentifier = tree.find('meteorologicalInformation')
            # bulletin.write()

            # A_LAXX00LTFJ000000_C_LTFJ_20210413121359.xml   ### the name will be similar

            # This part uses lxml writer to create version without bulletin number elements

            timestr = time.strftime("%Y%m%d%H%M%S")
            fileName = icaoID.text+"_IWXXM_File_XML_"+timestr+".xml"

            for xml in bulletin:

                parser = etree.XMLParser(recover=True)

                xmlRootNode = etree.fromstring(ET.tostring(xml))

                xmlstr = etree.tostring(
                    xmlRootNode, xml_declaration=True, encoding="UTF-8", pretty_print=True)

            if writeFile:
                with open(fileName, 'wb') as f:
                    f.write(etree.tostring(xmlRootNode, pretty_print=True))
                print(f'File in process: {fileName}')

            return fileName, xmlRootNode

        else:

            print("""

                            No gifts module exist for conversion!

                            Cannot install gift, please install manually!
                            ____________________________________________________

                            Apply steps below:

                          
                            !git clone https://github.com/NOAA-MDL/GIFTs.git

                            %cd GIFTs/

                            !python setup.py install --prefix=/usr/local

                            %cd ..
                            ____________________________________________________
                            """)


def main(argv):

    METARString, XMLConversion, XMLModification, ColorStateCal, CrossWindAlertCal, inputXMLurl, inputXMLPath, stationDesignator, searchMETARString, folderPathtoSearch = [
        None]*10

    try:
        opts, args = getopt.getopt(argv, "h", ["stationDesignator=", "METARString=", "XMLConversion", "XMLModification",
                                   "inputXMLPath=", "inputXMLurl=", "ColorState", "CrossWindAlert", "SearchMETARString", "folderPathtoSearch="])
    except getopt.GetoptError:
        print('MetocTools.py --XMLConversion --stationDesignator <ICOAStationDesign> --METARString <METARString>')

    for opt, arg in opts:
        print(arg)
        if opt == '-h':
            print('MetocTools.py --XMLConversion --stationDesignator <ICOAStationDesign> --METARString <METARString>')
            print('     Example: MetocTools.py --XMLConversion --stationDesignator LICZ --METARString "260750Z 26010KT 9999 SCT028 BKN070 06/M01 Q1023 NOSIG RMK RWY24 27009KT="')
            print(
                'MetocTools.py --XMLModification --inputXMLurl <URL> --ColorState --CrossWindAlert')
            print('     Example: MetocTools.py --XMLModification --inputXMLurl "http://www.meteocenter.ru/iwxxm/xml/A_LARU20UAKK130830_C_RUMS_20210413084323.xml" --ColorState --CrossWindAlert')
            print(
                'MetocTools.py --XMLModification --inputXMLPath <Path> --ColorState --CrossWindAlert')
            print('     Example: MetocTools.py --XMLModification --inputXMLPath "/content/LICZ_IWXXM_File_XML_20210429085650.xml" --ColorState --CrossWindAlert')
            print('MetocTools.py --SearchMETARString --folderPathtoSearch <SearchFolderPath> --stationDesignator <stationDesignator>')
            print('     Example: MetocTools.py --SearchMETARString --folderPathtoSearch "/content/content/SmallFiles4" --stationDesignator SECU')
            print('MetocTools.py --SearchMETARString --folderPathtoSearch <SearchFolderPath> --stationDesignator <stationDesignator> --XMLConversion')
            print('     Example: MetocTools.py --SearchMETARString --folderPathtoSearch "/content/content/SmallFiles4" --stationDesignator SECU --XMLConversion')

            sys.exit()
        elif opt in ("--stationDesignator"):
            stationDesignator = arg
        elif opt in ("--METARString"):
            METARString = arg
        elif opt in ("--XMLConversion"):
            XMLConversion = True
        elif opt in ("--XMLModification"):
            XMLModification = True
        elif opt in ("--ColorState"):
            ColorStateCal = True
        elif opt in ("--CrossWindAlert"):
            CrossWindAlertCal = True
        elif opt in ("--inputXMLPath"):
            inputXMLPath = arg
        elif opt in ("--inputXMLurl"):
            inputXMLurl = arg
        elif opt in ("--SearchMETARString"):
            searchMETARString = True
        elif opt in ("--folderPathtoSearch"):
            folderPathtoSearch = arg

    if all(i != None for i in [XMLConversion, METARString, stationDesignator]):
        metar2XML = Metar2XML(stationDesignator, METARString)
        fileName, _ = metar2XML.checkGIFTsModule_convertMETARstring2IWXXM()
        print("File has been created:", fileName)

    if all(i != None for i in [XMLModification, inputXMLurl]) or all(i != None for i in [XMLModification, inputXMLPath]):
        if inputXMLPath:
            url = os.path.expanduser(inputXMLPath)
            xmlRootNodeforMETAR, fileName = getXmlRootNode(
                url, "filePath", createFile=True)  # to access xml file from local path
            print(fileName)

        elif inputXMLurl:
            url = inputXMLurl
            xmlRootNodeforMETAR, fileName = getXmlRootNode(
                url, "url", createFile=True)
            print(fileName)
        # Check if file is exist

        if xmlRootNodeforMETAR != None:
            # TODO get the station information

            for element in xmlRootNodeforMETAR.iter():
                # To surpress elements were assigned first warning https://stackoverflow.com/questions/18583162/difference-between-if-obj-and-if-obj-is-not-none
                designatorElem1 = element.getroottree().getpath(element).endswith("designator")
                designatorElem2 = element.getroottree().getpath(
                    element).endswith("locationIndicatorICAO")
                if designatorElem1 == True and len(element.text) == 4:
                    stationDesignator = element.text
                elif designatorElem2 == True and len(element.text) == 4:
                    stationDesignator = element.text

            print(f"Modifying XML file for station:{stationDesignator}")

            # --------------------------   Get Station Information from file or API
            # assumes station file will be in same directory as the running script
            mainFolder = os.getcwd()
            # if not station folder in the directory, it will create it.

            folderPathForStationFiles = os.path.join(mainFolder, "stations")
            if not os.path.exists(folderPathForStationFiles):
                os.makedirs(folderPathForStationFiles)
                filePathforStationFile = os.path.join(
                    folderPathForStationFiles, stationDesignator+"_station.json")

            else:
                filePathforStationFile = os.path.join(
                    folderPathForStationFiles, stationDesignator+"_station.json")

            jsonResponseStation = getStationInfofromFile(
                filePathforStationFile)
            if jsonResponseStation == None:
                jsonResponseStation = getStationInfo(stationDesignator)
                writeStationInfoIntoFile(
                    jsonResponseStation, filePathforStationFile)
            else:
                print("Station Json file is taken from Local Folder")

            #print (jsonResponseStation)
            #print (xmlRootNodeforMETAR)

            # ----------------------------------------------------------------------
            # Now calculate parameters and modify xml file
            if stationDesignator != None:
                if CrossWindAlertCal:
                    crosswindforStation = CrossWind(
                        xmlRootNodeforMETAR, jsonResponseStation, metarFormatType="XML")
                    crosswindComponentForStation = crosswindforStation.calculateCrossWindComponent()
                    print(crosswindforStation)
                    fileName, _ = crosswindforStation.createModifiedIwxxmFileforCrossWind(
                        nameSpaceKey="iwxxm-nato", nameSpaceUrl="http://shape.nato.int", version="1.0", fileName=fileName)

                if ColorStateCal:
                    colorStateforStation = ColorState(
                        xmlRootNodeforMETAR, metarFormatType="XML")
                    colorStateforStation.calculateColorState()
                    print(colorStateforStation)
                    fileName, _ = colorStateforStation.createModifiedIwxxmFileforColorState(
                        nameSpaceKey="iwxxm-nato", nameSpaceUrl="http://shape.nato.int", version="1.0", fileName=fileName)
                print("File Created:", fileName)

    if all(i != None for i in [searchMETARString, folderPathtoSearch, stationDesignator]):

        try:
            sortedListOfFindMETARs, selectedMostUpdatedMetar = retriveMETARsforStationfromListofFiles(
                stationDesignator, folderPathtoSearch)

            for item in sortedListOfFindMETARs:

                print(item["raw"])

            for item in sortedListOfFindMETARs:

                print(item["parsedMetar"])

            metarRawString = selectedMostUpdatedMetar["raw"]
            #print (metarRawString)
            print("--------Most Recent Metar String----------")
            print(f'{metarRawString}')

            if XMLConversion:
                metar2XML = Metar2XML(stationDesignator, metarRawString)
                fileName = metar2XML.checkGIFTsModule_convertMETARstring2IWXXM()
                print("File Created:", fileName)

        except:
            print(
                f"No Metar string was found or no aerodrome for station designator:{stationDesignator}")


# This is manual tests
def tests():
    print("Option 1:Test with Json Metar from API ")
    print("Option 2:Test with Metar String ")
    print("Option 3:Test with XML Metar")
    print("Option 4:Test with Metar String Converted to XML")
    print("Option 5:Test with Metar String Converted to XML")

    #option=int(input("Set Option:"))
    option = 5
    stationDesignator = "LTFJ"

    mainFolder = os.getcwd()
    folderPathForStationFiles = os.path.join(mainFolder, "stations")
    if not os.path.exists(folderPathForStationFiles):
        os.makedirs(folderPathForStationFiles)

    # -------------------------------- Read Station Json if exists-----------------------------------

    filePathforStationFile = os.path.join(
        folderPathForStationFiles, stationDesignator+"_station.json")

    jsonResponseStation = getStationInfofromFile(filePathforStationFile)

    print("Station Json file is taken from Local Folder")

    if jsonResponseStation == None:

        jsonResponseStation = getStationInfo(stationDesignator)

        writeStationInfoIntoFile(jsonResponseStation, filePathforStationFile)

        print("Station Json file is taken from API Call")

    print(jsonResponseStation)
    print("==========================================================")

    # -------------------------------- Test: Convert METAR String to XML -----------------------------------
    if option == 0:
        metarString = "260750Z 26010KT 9999 SCT028 BKN070 06/M01 Q1023 NOSIG RMK RWY24 27009KT="
        metar2XML = Metar2XML(stationDesignator, metarString)
        fileName = metar2XML.checkGIFTsModule_convertMETARstring2IWXXM()

    if option == 1:

        # -------------------------------- Test with Json Metar from API---------------------------------------

        jsonResponseMetar = getMetarInfo(stationDesignator)

        print(jsonResponseMetar)

        # Calculate ColorWind Component

        crosswindforStation = CrossWind(
            jsonResponseMetar, jsonResponseStation, metarFormatType="avwx_JSON")

        crosswindComponentForStation = crosswindforStation.calculateCrossWindComponent()

        #print (crosswindComponentForStation)

        # if crosswindComponentForStation!=None:

        #        for idx,item in enumerate(crosswindComponentForStation):

        #          windSpeed,windDirection,runwayDirection,angleBetweenRunwayAndWind,crossWindComponent=crosswindComponentForStation[idx]

        #          print("------------------------------------------Runway:",idx)

        #          print("windSpeed:",windSpeed)

        #          print("windDirection:",windDirection)

        #          print("runwayDirection:",runwayDirection)

        #          print("angleBetweenRunwayAndWind:",angleBetweenRunwayAndWind)

        #          print("crossWindComponent:",crossWindComponent)

        # print section replaced with overwritten __str__
        print(crosswindforStation)

        # Calculate ColorState

        colorStateforStation = ColorState(
            jsonResponseMetar, metarFormatType="avwx_JSON")

        colorStateforStation.calculateColorState()

        print(colorStateforStation)

        # Calculate Map Properties for CrossWind and Display on the Map

        runwayGDF = crosswindforStation.getRunwayLineGeodataFrame()

        windGDF = crosswindforStation.getWindDirectionGedataFrame()

        # crosswindforStation.displayMap()

    elif option == 2:

        # -------------------------------- Test with Metar String ---------------------------------------

        print('-------------------------------- Test with Metar String ---------------------------------------')

        #metarRawString=stationDesignator+" 062355Z 27008KT CAVOK 14/12 Q1010 RMK SKC VIS MIN 9999 WIND"

        #metarRawString="METAR "+ stationDesignator+" 011350Z 04005KT 300V080 9999 SCT040 BKN090 15/10 Q1011"

        metarRawString = input("METAR String after station:")

        metarRawString = "METAR " + stationDesignator+" "+metarRawString

        # Calculate ColorWind Component

        crosswindforStation = CrossWind(
            metarRawString, jsonResponseStation, metarFormatType="raw_String")

        crosswindComponentForStation = crosswindforStation.calculateCrossWindComponent()

        # print section replaced with overwritten __str__
        print(crosswindforStation)

        # Calculate ColorState

        colorStateforStation = ColorState(
            metarRawString, metarFormatType="raw_String")

        colorStateforStation.calculateColorState()

        print(colorStateforStation)

        # Calculate Map Properties for CrossWind and Display on the Map

        runwayGDF = crosswindforStation.getRunwayLineGeodataFrame()

        windGDF = crosswindforStation.getWindDirectionGedataFrame()

        # crosswindforStation.displayMap()

        # -------------------------------- Test with Test with XML Metar ---------------------------------------

    elif option == 3:

        print('-------------------------------- Test with Test with XML Metar ---------------------------------------')

        # Test with XML Metar

        # url="http://www.meteocenter.ru/iwxxm/xml/A_LARU20UAAA101330_C_RUMS_20210310133757.xml"

        print("Option 1: XML from Url")
        print("Option 2: XML file Path")

        urlOrXMLFile = int(input("Option for XML file:"))

        if urlOrXMLFile == 1:
            # url="http://www.meteocenter.ru/iwxxm/xml/A_LARU20UAKK130830_C_RUMS_20210413084323.xml" ### Some xml with CAVOK

            url = input("XML from Url:")
            xmlRootNodeforMETAR, fileName = getXmlRootNode(
                url, "url", createFile=True)

        elif urlOrXMLFile == 2:
            url = os.path.expanduser(input("Path for XLM file:"))
            xmlRootNodeforMETAR, fileName = getXmlRootNode(
                url, "filePath", createFile=False)  # to access xml file from local path

        # Calculate ColorWind Component

        crosswindforStation = CrossWind(
            xmlRootNodeforMETAR, jsonResponseStation, metarFormatType="XML")

        crosswindComponentForStation = crosswindforStation.calculateCrossWindComponent()

        # print section replaced with overwritten __str__
        print(crosswindforStation)

        # Calculate ColorState

        colorStateforStation = ColorState(
            xmlRootNodeforMETAR, metarFormatType="XML")

        colorStateforStation.calculateColorState()

        print(colorStateforStation)

        # Calculate Map Properties for CrossWind and Display on the Map

        runwayGDF = crosswindforStation.getRunwayLineGeodataFrame()

        windGDF = crosswindforStation.getWindDirectionGedataFrame()

        # crosswindforStation.displayMap()

    elif option == 4:

        # -------------------------------- Test with Test with Metar String Converted to XML ---------------------------------------

        print('-------------------------------- Test with Test with Metar String Converted to XML ---------------------------------------')

        metarRawString = input("METAR String after station:")

        metarRawString = "METAR " + stationDesignator+" "+metarRawString

        # First Convert the Metar string to IWXXM file

        # stationDesignator="LTAC" ###"PHNL" ###"LTAC"

        # -------------------------------- Read Station Json if exists----------------------------------

        # print(calculateCrossWindComponent(jsonResponseMetar,jsonResponseStation,metarFormatType="avwx_JSON"))

        #metarRawString="METAR "+stationDesignator+" 011350Z 04005KT 300V080 9999 SCT040 BKN090 15/10 Q1011"

        #metarRawString="METAR UAAA 011350Z 04005KT 300V080 9999 SCT040 BKN090 15/10 Q1011="

        #print (metarRawString)

        #metarRawString="METAR LTFJ 260750Z 26010KT 9999 SCT028 BKN070 06/M01 Q1023 NOSIG RMK RWY24 27009KT="

        metar2XML = Metar2XML(stationDesignator, metarRawString)
        fileName, _ = metar2XML.checkGIFTsModule_convertMETARstring2IWXXM(
            aerodromesDBPath=os.path.join(mainFolder, "aerodromes2.db"))

        xmlRootNodeforMETAR, fileName = getXmlRootNode(
            "./"+fileName, "filePath", createFile=False)  # to access xml file from local path

        #xmlRootNodeforMETAR,fileName=getXmlRootNode(url,"url",createFile=True)  ##

        # Calculate ColorWind Component

        crosswindforStation = CrossWind(
            xmlRootNodeforMETAR, jsonResponseStation, metarFormatType="XML")

        crosswindComponentForStation = crosswindforStation.calculateCrossWindComponent()

        # print section replaced with overwritten __str__
        print(crosswindforStation)

        # Calculate ColorState

        colorStateforStation = ColorState(
            xmlRootNodeforMETAR, metarFormatType="XML")

        colorStateforStation.calculateColorState()

        print(colorStateforStation)

        # Calculate Map Properties for CrossWind and Display on the Map

        runwayGDF = crosswindforStation.getRunwayLineGeodataFrame()

        windGDF = crosswindforStation.getWindDirectionGedataFrame()

        # crosswindforStation.displayMap()

        # Adds calculated parameters at the end of XML file

        fileName, _ = crosswindforStation.createModifiedIwxxmFileforCrossWind(
            nameSpaceKey="iwxxm-nato", nameSpaceUrl="http://shape.nato.int", version="1.0", fileName=fileName, writeFile=True)

        fileName, _ = colorStateforStation.createModifiedIwxxmFileforColorState(
            nameSpaceKey="iwxxm-nato", nameSpaceUrl="http://shape.nato.int", version="1.0", fileName=fileName, writeFile=True)

        # Test for finding the most recent metar and calculate parameters

    elif option == 5:

        # -------------------------------- Find the most recent metars string by crawling the files -----------------------------------

        # stationDesignator="LICZ"

        folderPathforFilles = "./content/parsedfiles2"

        #folderPathforFilles=os.path.expanduser(input( "FolderPath for Metardata:"))

        print(folderPathforFilles)

        sortedListOfFindMETARs, selectedMostUpdatedMetar = retriveMETARsforStationfromListofFiles(
            stationDesignator, folderPathforFilles)

        print(f'Most recent Metar:{selectedMostUpdatedMetar["raw"]}"')

        for item in sortedListOfFindMETARs:

            print(item["raw"])

        for item in sortedListOfFindMETARs:

            print(item["parsedMetar"])

        metarRawString = selectedMostUpdatedMetar["raw"]

        # -------------------------------- Read Station Json if exists-----------------------------------

        filePathforStationFile = folderPathForStationFiles + \
            "/"+stationDesignator+"_station.json"

        jsonResponseStation = getStationInfofromFile(filePathforStationFile)

        if jsonResponseStation == None:

            jsonResponseStation = getStationInfo(stationDesignator)

            writeStationInfoIntoFile(
                jsonResponseStation, filePathforStationFile)

        # print(calculateCrossWindComponent(jsonResponseMetar,jsonResponseStation,metarFormatType="avwx_JSON"))

        # -------------------------------- Test with Metar String-----------------------------------

        crosswindforStation = CrossWind(
            metarRawString, jsonResponseStation, metarFormatType="raw_String")

        crosswindComponentForStation = crosswindforStation.calculateCrossWindComponent()

        # print section replaced with overwritten __str__
        print(crosswindforStation)

        runwayGDF = crosswindforStation.getRunwayLineGeodataFrame()

        windGDF = crosswindforStation.getWindDirectionGedataFrame()

        # crosswindforStation.displayMap()

        colorStateforStation = ColorState(
            metarRawString, metarFormatType="raw_String")

        colorStateforStation.calculateColorState()

        print(colorStateforStation.colorState)


if __name__ == "__main__":
    main(sys.argv[1:])
    # tests()
