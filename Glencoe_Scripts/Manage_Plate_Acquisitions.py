# coding=utf-8
"""
-----------------------------------------------------------------------------
  Copyright (C) 2013 Glencoe Software, Inc. All rights reserved.


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

------------------------------------------------------------------------------

Add or remove PlateAcquisition(s) in a given Plate.
"""
from omero.util import script_utils
from omero.gateway import BlitzGateway
from omero.rtypes import *
from omero.model import *
import omero.scripts as scripts


def run():
    """
    """
    dataTypes = [rstring("Plate")]
    
    client = scripts.client("Manage_Plate_Acquisitions.py",
        "Add or remove PlateAcquisition(s) in a given Plate",
        
        scripts.String("Data_Type", optional=False, grouping="1",
            description="The data type you want to work with.", 
            values=dataTypes, 
            default="Plate",
        ),
        
        scripts.List("IDs", optional=False, grouping="2",
            description="List of Plate IDs",
        ).ofType(rlong(0)),
        
        scripts.String("Mode", optional=False, grouping="3",
            description="Select if you want to add or remove PlateAcquisitions",
            values=[rstring("Add"), rstring("Remove")],
            default="Add",
        ),
        
        version = "0.2",
        authors = ["Niko Klaric"],
        institutions = ["Glencoe Software Inc."],
        contact = "support@glencoesoftware.com",
    )

    try:
        scriptParams = {}
        for key in client.getInputKeys():
            if client.getInput(key):
                scriptParams[key] = client.getInput(key, unwrap=True)

        connection = BlitzGateway(client_obj=client)
        updateService = connection.getUpdateService()
        queryService = connection.getQueryService()

        processedMessages = []

        for plateId in scriptParams["IDs"]:
            plateObj = connection.getObject("Plate", plateId)
            if plateObj is None:
                client.setOutput("Message",
                    rstring("ERROR: No Plate with ID %s" % plateId))
                return

            if scriptParams["Mode"] == "Add":
                plateAcquisitionObj = PlateAcquisitionI()
                plateAcquisitionObj.setPlate(PlateI(plateObj.getId(), False))

                wellGrid = plateObj.getWellGrid()
                for axis in wellGrid:
                    for wellObj in axis:
                        wellSampleList = wellObj.copyWellSamples()
                        plateAcquisitionObj.addAllWellSampleSet(wellSampleList)

                plateAcquisitionObj = updateService.saveAndReturnObject(
                    plateAcquisitionObj)
                plateAcquisitionId = plateAcquisitionObj.getId()._val

                processedMessages.append(
                    "Linked new PlateAcquisition with ID %d to Plate with ID %d."
                        % (plateAcquisitionId, plateId))
            else:
                params = omero.sys.ParametersI()
                params.addId(plateId)

                queryString = """
                    FROM PlateAcquisition AS pa
                    LEFT JOIN FETCH pa.wellSample
                    LEFT OUTER JOIN FETCH pa.annotationLinks
                        WHERE pa.plate.id = :id
                    """
                plateAcquisitionList = queryService.findAllByQuery(
                    queryString, params, connection.SERVICE_OPTS)
                if plateAcquisitionList:
                    updateList = []

                    for plateAcquisitionObj in plateAcquisitionList:
                        for wellSampleObj in plateAcquisitionObj.copyWellSample():
                            wellSampleObj.setPlateAcquisition(None)
                            updateList.append(wellSampleObj)

                        updateService.saveArray(updateList)

                        plateAcquisitionObj.clearWellSample()
                        plateAcquisitionObj.clearAnnotationLinks()

                        plateAcquisitionObj = updateService.saveAndReturnObject(
                            plateAcquisitionObj)
                        updateService.deleteObject(plateAcquisitionObj)

                processedMessages.append(
                    "%d PlateAcquisition(s) removed from Plate with ID %d."
                        % (len(plateAcquisitionList), plateId))

        client.setOutput("Message", rstring("No errors. %s"
            % " ".join(processedMessages)))
    finally:
        client.closeSession()

if __name__ == "__main__":
    run()
