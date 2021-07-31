


*  Swagger-Flask-Web API for Metar to IWXXM XML conversion  

** A python console application and a swagger based web application has been created to provide conversion between METAR string and XML file as well as calculation of ColorState and CrossWindAlert. 

The script created for console application can be used;
To convert a user given METAR string to IWXXM format XML file.
To modify an existing XML document in IWXXM format and, add ColorState and CrossWindAlert with “iwxxm-nato” XML elements under remarks by providing a file given in a URL or a direct path. 
Additionally, it can search multiple hourly message files to find the recent message of the user given station designator for all METAR string within each bulletin file (SAXXXX), with the optional parameter to generate an IWXXM format XML file. (not applicable with the web service application) 
 
External Code Sources
The script uses some external components and sources that are directly used or modified. 
avwx-engine: Aviation weather report parsing library that allows to both parsing TAC format data and requests METAR data and station information from AVWX REST API (2021). This is an open-source and publicly available API providing weather data within the daily limit. The avwx-engine repository is maintained by DuPont (2021). 
GIFTs: The python desktop software created by NOAA to generate IWXXM From TAC (Oberfield,2021). The software is created as a stand-alone desktop application. To conversion in the console application, its “demo.py” file is modified in a way that is accepting any METAR string to generate an IWXXM file.  
 
The GIFTs repository does not have the full aerodrome database and it requires generating a new one for each airport that will be queried. GML attributes contain the coordinates for each airport for the generated XML file. This information is acquired from a locally generated aerodrome database. The created functions to generate .tbl to .db from the airport.csv file were included but the elevation information of each airport was assumed to be 0 as the airport data found online does not contain this information. The airport data can be replaced with a more precise one for production use. ** 


* Usage

- app.py is running swagger web application in the localhost. MetocTools.py, requirement.txt, static folder containing swagger.json, station folder containing json files for stations and aerodromes for stations are neccesary for application. 

- Once the docker application working on the server side (in our case we will be using localhost).  

The Dockerfile containing the necessary commands can be used to build docker image for metoctools.  

1. Build docker image for metoctools.

docker  build -t metoctool .  

2. Run docker container with port 5001

docker run -p 5001:5001 metoctool

The application will be running in 0.0.0.0:5001 or 127.0.0.1:5001 depending on swagger.json configuration. Use Firefox to test the running application.

![Swagger-Flask API for IWXXM](/image11-54.jpg)

