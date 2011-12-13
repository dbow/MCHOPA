import cgi
import os
import re
import string
import csv

from google.appengine.ext import webapp
from google.appengine.ext import db

from google.appengine.ext.webapp import template
from google.appengine.ext.db import djangoforms

from google.appengine.ext.webapp.util import run_wsgi_app



#Painting outlines the database entity for the paintings
class Painting(db.Model):
  idnumber = db.IntegerProperty()
  title = db.StringProperty(required=True)
  description = db.StringProperty(multiline=True, required=True)
  filename = db.StringProperty(required=True)
  size = db.StringProperty(required=True, choices=['10x14', '12x28', '17x28', '23x31', '20x24',])
  price = db.IntegerProperty(required=True)
  series = db.StringProperty(choices=['','Classic', 'Illustrative', 'Abstract'])
  status = db.StringProperty(required=True, choices=['Available', 'Sold', 'Reserved'])

#PaintingForm uses a djangoforms ModelForm template to construct the form to populate Painting
class PaintingForm(djangoforms.ModelForm):
  class Meta:
    model = Painting
    exclude = ['idnumber']


#This class constructs the admin dashboard, listing all the paintings and any messages based on URL parameters
class AdminDashboard(webapp.RequestHandler):
  def get(self):
    paintings = db.GqlQuery("SELECT * FROM Painting ORDER BY idnumber")

    #Extract any URL parameters
    error = self.request.get('error')
    added = self.request.get('added')
    dup = self.request.get('dup')
    deleted = self.request.get('deleted')

    #Display messages based on those parameters
    if error == str(0):
      error = "Please attach an Excel CSV file to upload"
    if error == str(1):
      error = "CSV file must have the following headers exactly: 'Title,Description,Series,Size,Price,Status,Filename'"
    if added:
      added = str(added) + ' painting(s) added to the database.'
    if deleted:
      deleted = '1 painting deleted'
    if dup:
      dup = str(dup) + ' painting(s) filtered out as duplicates.'

    template_values = {
		    'paintings': paintings,
            'error': error,
            'added': added,
            'dup': dup,
            'deleted': deleted,
		    }
    path = os.path.join(os.path.dirname(__file__), 'admin/admin.html')
    self.response.out.write(template.render(path, template_values))

#This method takes a painting and checks to make sure that the title or filename do not already exist in the database
def dedup(painting):
  allpaintings = Painting.all()
  titles = []
  filenames = []

  #Create lists of all titles and filenames currently in the database
  for allpainting in allpaintings:
    titles.append(allpainting.title)
    filenames.append(allpainting.filename)

  dup = False

  #Check if the title already exists in the database
  if painting.title in titles:
    dup = True

  #Check if the filename already exists in the database
  if painting.filename in filenames:
    dup = True

  return dup
    

#This class is used to create a new painting on a one-off basis
class CreatePainting(webapp.RequestHandler):

  #The get method constructs an empty PaintingForm
  def get(self):
    paintingform = PaintingForm()
    url = 'create'
    template_values = {
            'url': url,
            'paintingform': paintingform,
		    'text': "Create new",
		    }
    path = os.path.join(os.path.dirname(__file__), 'admin/painting.html')
    self.response.out.write(template.render(path, template_values))


  #The post method takes the data from the form and puts it in the database
  def post(self):
    data = PaintingForm(data=self.request.POST)

    #Verifies that the data is formatted correctly
    if data.is_valid():
      entity = data.save(commit=False)

      #Checks if the entry is a duplicate
      isdup = dedup(entity)

      #If it is a duplicate, the form is repopulated with an error message
      if isdup:
        paintingform = data
        error = "Title or filename already exists"
        url = 'create'

        template_values = {
              'error': error,
              'url': url,
              'paintingform': paintingform,
              'text': "Create new",
              }
        path = os.path.join(os.path.dirname(__file__), 'admin/painting.html')
        self.response.out.write(template.render(path, template_values))

      #If it is not a duplicate, the data is put in the database
      else:

        #The idnumber is set to be 1 higher than the last painting's idnumber
        paintings = db.GqlQuery("SELECT * FROM Painting ORDER BY idnumber DESC").fetch(1)
        if paintings:
          lastpainting = paintings[0]
          r = lastpainting.idnumber
        else:
          r = 0
        entity.idnumber = r + 1

        #Data is stored in the database
        entity.put()
        self.redirect('/admin?added=1')

    #If the data is not formatted correctly, the form is recreated with form-specific error messaging
    else:
      paintingform = data
      url = 'create'
      template_values = {
            'url': url,
            'paintingform': paintingform,
            'text': "Create new",
            }
      path = os.path.join(os.path.dirname(__file__), 'admin/painting.html')
      self.response.out.write(template.render(path, template_values))


#This class is used to bulk upload paintings into the database with a CSV file
class CSVUpload(webapp.RequestHandler):

  def post(self):
    form = cgi.FieldStorage()
    csvfile = form["csvupload"].file

    #Verifies that the header of the file is formatted correctly
    header = csvfile.readline()
    if header:

      #If it is not formatted correctly, an error message is displayed
      if re.match('Title,Description,Series,Size,Price,Status,Filename', re.sub('\r\n',"",header)) == None:
        self.redirect('/admin?error=' + header)
      
      else:

        #Extracts the idnumber of the last painting in the database
        q = db.GqlQuery("SELECT * FROM Painting ORDER BY idnumber DESC")
        paintings = q.fetch(1)
        if paintings:
          lastpainting = paintings[0]
          r = lastpainting.idnumber
        else:
          r = 0

        #Instantiates tracking variables for number of duplicates and number of paintings added
        dup = 0
        added = 0

        #Using the csv module's reader class, reads each row and assigns the data to the appropriate variable
        csvReader = csv.reader(form["csvupload"].file, dialect=csv.excel)
        for row in csvReader:
          new_idnumber = r + 1
          new_title = row[0]
          new_description = row[1]
          new_series = row[2]
          new_size = row[3]
          new_price = int(row[4])
          new_status = row[5]
          new_filename = row[6]

          #Creates a new painting with variables based on that row's data
          newpainting = Painting(idnumber=new_idnumber, title=new_title, description=new_description, series=new_series, size=new_size, price=new_price, status=new_status, filename=new_filename)

          #Checks if the painting already exists in the database
          isdup = dedup(newpainting)

          #If so, it counts it as a duplicate and does not add it again
          if isdup:
            dup = dup + 1

          #If not, it adds it to the database and counts it as 'added'
          else:
            newpainting.put()
            added = added + 1
            r = r + 1

        #If there are any duplicates, the number is displayed (along with the number added)
        if dup:
          self.redirect('/admin?added=' + str(added) + '&dup=' + str(dup))

        #If there are no duplicates, only the number added is displayed
        else:
          self.redirect('/admin?added=' + str(added))

    #If there is no header (i.e. no file), an error message is displayed
    else:
      self.redirect('/admin?error=0')
 

#This class is used to edit a painting that already exists in the database
class EditPainting(webapp.RequestHandler):

  #The get method creates an instance of PaintingForm with the selected painting's data populated
  def get(self):
    
    #Extracts the painting id from the URL and queries the database for that painting
    id = self.request.get('id')
    query = db.GqlQuery("SELECT * FROM Painting WHERE idnumber = %s" % id)
    painting = query.get()
    
    #Creates an instance of PaintingForm with that painting's data
    paintingform = PaintingForm(instance=painting)

    #Creates the url variable to go in the form template
    url = 'edit?id=' + str(id)

    template_values = {
            'url': url,
            'id': id,
            'paintingform': paintingform,
		    'text': "Update",
		    }

    path = os.path.join(os.path.dirname(__file__), 'admin/painting.html')
    self.response.out.write(template.render(path, template_values))

  #The post method extracts the data from the form for that specific painting and adds it to the database
  def post(self):
    
    #Extracts the id from the URL and queries for that specific painting
    id = self.request.get('id')
    query = db.GqlQuery("SELECT * FROM Painting WHERE idnumber = %s" % id)
    painting = query.get()

    #Extracts the data from the form
    data = PaintingForm(data=self.request.POST, instance=painting)

    #Checks that the data conforms to the database parameters
    if data.is_valid():

      # Save the data, and redirect to the view page
      entity = data.save(commit=False)

      #Data is stored in the database
      entity.put()
      self.redirect('/admin')

    else:
      # Reprint the form with appropriate error messaging
      paintingform = data
      url = 'edit?id=' + str(id)

      template_values = {
            'url': url,
            'id': id,
            'paintingform': paintingform,
            'text': "Update",
            }

      path = os.path.join(os.path.dirname(__file__), 'admin/painting.html')
      self.response.out.write(template.render(path, template_values))


#This class deletes the painting of a given idnumber from the database
class DeletePainting(webapp.RequestHandler):

  def get(self):
    
    #Extracts the id number from the URL and queries the database for that painting
    id = self.request.get('id')
    product = db.GqlQuery("SELECT * FROM Painting WHERE idnumber = %s" % id)

    #Deletes the painting from the database
    db.delete(product)
    self.redirect('/admin?deleted=1')




#This is webapp application constructor for the admin pages, which constructs pages using the classes above based on the URL provided
application = webapp.WSGIApplication ([('/admin', AdminDashboard),
                                       ('/admin/delete', DeletePainting),
				                               ('/admin/create', CreatePainting),
				                               ('/admin/csvupload', CSVUpload),
				                               ('/admin/edit', EditPainting)],
				                              debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
