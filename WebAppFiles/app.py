#!/usr/bin/env python3
##################################################
# This swagger web application provides funtionalities;
#       To convert a user given METAR string to IWXXM format XML file.
#       To modify an existing XML document in IWXXM format and, add ColorState and CrossWindAlert
# with “iwxxm-nato” XML elements under remarks by providing a file given in a URL or a direct path. 
##################################################
# Author: Naime Celik
# Last Modified: 2021/05/20
##################################################
## Use Docker container to run this application
##################################################

from flask import Flask, jsonify, request,redirect,make_response,send_from_directory, send_file,Response
import MetocTools as MT
from flask_swagger_ui import get_swaggerui_blueprint
import os
import datetime
import pandas as pd
from flask_cors import CORS
import os
from lxml import etree

# creating a Flask app 
app = Flask(__name__) 
CORS(app,expose_headers=["x-suggested-filename","content-disposition"])

#from flask_ngrok import run_with_ngrok
#run_with_ngrok(app)   

from flask import render_template,url_for,redirect,request,session

### swagger specific ###
SWAGGER_URL = ''
API_URL = '/static/swagger.json'
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Metoc Transformation API"
    },

)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)

from io import BytesIO    
from lxml import etree


### Convert from Metar string to XML 
@app.route('/XMLConversion', methods = ['GET']) 
def XMLConversionfromMetarString():
    stationDesignator = request.args.get('stationDesignator')
    metarString = request.args.get('metarString')
    if request.method == 'GET'or request.method == 'POST':
        bufferFile = BytesIO()

        print (stationDesignator)
        print (metarString)
        metar2XML=MT.Metar2XML(stationDesignator,metarString)
        fileName, xmlRootNode =metar2XML.checkGIFTsModule_convertMETARstring2IWXXM(writeFile=False) 
        xml_str = etree.tostring(xmlRootNode,
                                    pretty_print=True,
                                    xml_declaration=True,
                                    encoding='UTF-8')
        bufferFile.write(xml_str)
        print ("File has been created:",fileName)
        #return jsonify({metar2XML.xmlRootNode})
        #return Response(xmlRootNode, mimetype='text/xml')
        #return jsonify(name=fileName, data=fileName)
        #return send_file(fileName,  mimetype='application/xml')
        bufferFile.seek(0)
        return send_file(bufferFile, as_attachment=True,
                     attachment_filename=fileName,
                     mimetype='application/xml')


@app.route('/XMLModify', methods=['GET', 'POST'])
def XMLModifyFromXMLFile():
    if request.method=='POST':
        ColorStateCal = request.values.get("colorState")
        CrossWindAlertCal = request.values.get("crossWindAlert")
        iFile = request.files.getlist('IWXXM_XML')[0]
        fileName=iFile.filename
        fileContent=iFile.read()
        print (CrossWindAlertCal)
        xmlRootNode = etree.fromstring(fileContent)
        print (xmlRootNode)
        stationDesignator=None
        if xmlRootNode!=None:
                for element in xmlRootNode.iter():
                       print(element)
                       ### To surpress elements were assigned first warning https://stackoverflow.com/questions/18583162/difference-between-if-obj-and-if-obj-is-not-none
                       designatorElem1=element.getroottree().getpath(element).endswith("designator")
                       designatorElem2=element.getroottree().getpath(element).endswith("locationIndicatorICAO")
                       if  designatorElem1==True and len(element.text)==4:
                          stationDesignator=element.text
                       elif designatorElem2==True and len(element.text)==4:
                          stationDesignator=element.text

                if stationDesignator!=None:
                    mainFolder=os.getcwd()  ### assumes station file will be in same directory as the running script
                    folderPathForStationFiles=os.path.join(mainFolder,"stations")
                    if not os.path.exists(folderPathForStationFiles):
                        os.makedirs(folderPathForStationFiles)
                        filePathforStationFile=os.path.join(folderPathForStationFiles,stationDesignator+"_station.json")
                    else:
                        filePathforStationFile=os.path.join(folderPathForStationFiles,stationDesignator+"_station.json")

                    jsonResponseStation=MT.getStationInfofromFile(filePathforStationFile)
                    if jsonResponseStation==None:
                        jsonResponseStation=MT.getStationInfo(stationDesignator)
                        MT.writeStationInfoIntoFile(jsonResponseStation,filePathforStationFile)
                    else:
                        print ("Station Json file is taken from Local Folder")
                 
                    ##----------------------------------------------------------------------
                    ## Now calculate parameters and modify xml file
                    if CrossWindAlertCal=="true":
                            print("here1")
                            crosswindforStation= MT.CrossWind(xmlRootNode,jsonResponseStation,metarFormatType="XML")
                            crosswindComponentForStation=crosswindforStation.calculateCrossWindComponent()
                            print(crosswindforStation)
                            fileName,xmlRootNode=crosswindforStation.createModifiedIwxxmFileforCrossWind(nameSpaceKey="iwxxm-nato",nameSpaceUrl="http://shape.nato.int",version="1.0",fileName=fileName,writeFile=False,readFileContent=xmlRootNode)

                    if ColorStateCal=="true":
                            colorStateforStation= MT.ColorState(xmlRootNode,metarFormatType="XML")
                            colorStateforStation.calculateColorState()
                            print(colorStateforStation)
                            fileName,xmlRootNode=colorStateforStation.createModifiedIwxxmFileforColorState(nameSpaceKey="iwxxm-nato",nameSpaceUrl="http://shape.nato.int",version="1.0", fileName=fileName,writeFile=False,readFileContent=xmlRootNode)
                    
                    print ("File Created:",fileName)
                    bufferFile = BytesIO()
                    xml_str = etree.tostring(xmlRootNode,
                                    pretty_print=True,
                                    xml_declaration=True,
                                    encoding='UTF-8')
                    bufferFile.write(xml_str)
                    bufferFile.seek(0)

                    result=send_file(bufferFile, as_attachment=True,
                     attachment_filename=fileName,
                     mimetype='application/xml')
                    result.headers["x-suggested-filename"] = fileName

                    return result


### TODO for future: 
### Check for existing element to avoid element dublicates
### Add exceptions for cases such as no cloid layers or aedronome info 

# driver function 
if __name__ == '__main__':
    app.run(debug = True,port=5001,host='0.0.0.0') #host='0.0.0.0 