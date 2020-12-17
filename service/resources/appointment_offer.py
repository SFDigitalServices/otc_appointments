"""Email module"""
#pylint: disable=too-few-public-methods
import json
import os
import falcon
import requests
from mako.template import Template
import sendgrid
from sendgrid.helpers.mail import Email, To, Content, Mail
from .hooks import validate_access

FROM_EMAIL = "no-reply@sf.gov"
SUBJECT = "Appointment Offering"
SPREADSHEETS_MICROSERVICE_URL = os.environ.get("SPREADSHEETS_MICROSERVICE_URL")
SPREADSHEETS_MICROSERVICE_API_KEY = os.environ.get("SPREADSHEETS_MICROSERVICE_API_KEY")
SPREADSHEET_KEY = os.environ.get("SPREADSHEET_KEY")
SPREADSHEETS_ID_COL = "A"
SPREADSHEETS_RESPONSE_COL = "AL"
SITE_DOMAIN = os.environ.get("SITE_DOMAIN")
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

@falcon.before(validate_access)
class EmailOffer():
    """EmailOffer class"""
    def on_post(self, _req, resp):
        #pylint: disable=no-self-use
        """
            Send email to offer a new appointment
        """
        request_body = _req.bounded_stream.read()
        request_params_json = json.loads(request_body)
        template = Template(filename="templates/appointment_offer.html")

        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY) #pylint: disable=invalid-name
        from_email = Email(FROM_EMAIL)
        to_email = To(request_params_json.get("to"))
        content = Content("text/html", template.render(
            site=SITE_DOMAIN,
            id=request_params_json.get('id'),
            name=request_params_json.get('name'),
            newDate=request_params_json.get('newDate'),
            newTime=request_params_json.get('newTime'),
            oldDate=request_params_json.get('oldDate'),
            oldTime=request_params_json.get('oldTime')
        ))
        mail = Mail(from_email, to_email, SUBJECT, content)
        response = sg.client.mail.send.post(request_body=mail.get())
        print(response.status_code)
        print(response.body)
        print(response.headers)
        resp.body = response.body
        resp.status_code = falcon.HTTP_200

class OfferResponse():
    """record applicant response to the offer"""
    def on_get(self, _req, resp):
        #pyint: disable=no-self-use
        """
            write the response to google sheet
        """
        try:
            data = create_spreadsheets_json()
            data["label_value_map"] = {
                SPREADSHEETS_RESPONSE_COL: _req.params.get('action')
            }
            print(data)

            response = requests.patch(
                url='{0}/rows/{1}'.format(SPREADSHEETS_MICROSERVICE_URL, _req.params.get('id')),
                headers=get_request_headers(),
                json=data
            )
            response.raise_for_status()
        except requests.HTTPError as err:
            print("HTTPError:")
            print("{0} {1}".format(err.response.status_code, err.response.text))
            resp.status = falcon.get_http_status(err.response.status_code)
            resp.body = json.dumps(err.response.json())

def get_request_headers():
    """
        headers for request to spreadsheets microservice
    """
    return {
        'x-apikey': SPREADSHEETS_MICROSERVICE_API_KEY
    }

def create_spreadsheets_json():
    return {
        "spreadsheet_key": SPREADSHEET_KEY,
        "worksheet_title": "Sheet1",
        "id_column_label": SPREADSHEETS_ID_COL,
    }