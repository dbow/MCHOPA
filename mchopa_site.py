import cgi
import os
import re
import string
import math

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template

#The Painting class is the database entity for the stored paintings
class Painting(db.Model):
  idnumber = db.IntegerProperty()
  title = db.StringProperty()
  description = db.StringProperty(multiline=True)
  filename = db.StringProperty()
  size = db.StringProperty()
  price = db.IntegerProperty()
  series = db.StringProperty()
  status = db.StringProperty()

def escape(value):

  html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
    }


  """Produce entities within text."""
  return "".join(html_escape_table.get(c,c) for c in value)

#The Home class constructs the homepage with no template variables
class Home(webapp.RequestHandler):
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
    self.response.out.write(template.render(path, {}))

#The Bio class constructs the Bio page with no template variables
class Bio(webapp.RequestHandler):
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'templates/bio.html')
    self.response.out.write(template.render(path, {}))

#The Inspiration class constructs the Inspiration page with no template variables
class Inspiration(webapp.RequestHandler):
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'templates/inspiration.html')
    self.response.out.write(template.render(path, {}))

#The Gallery class constructs the Gallery pages based on URL variables
class Gallery(webapp.RequestHandler):

  def get(self):
    #Extract any filtering variables
    filter = escape(self.request.get("filter"))
    value = escape(self.request.get("value"))
    order = escape(self.request.get("order"))

    #Construct the filtering hashes
    valuemap = {'classic':'Classic', 'illustrative':'Illustrative', 'abstract':'Abstract', '10x14':'10x14', '12x28':'12x28', '17x28':'17x28', '23x31':'23x31', '20x24':'20x24'}
    ordermap = {'':'idnumber', 'asc':'price', 'desc':'price DESC'}

    #Setting up the query to pull paintings from the database based on the filters provided
    if filter:
      paintingquery = db.GqlQuery("SELECT * FROM Painting WHERE %s = '%s' ORDER BY %s" % (filter, valuemap[value], ordermap[order]))
    else:
      paintingquery = db.GqlQuery("SELECT * FROM Painting ORDER BY %s" % (ordermap[order]))

    #Calculate the total number of pages (max) to display the paintings in the query in increments of PAGESIZE
    PAGESIZE = 5
    allpaintings = paintingquery.fetch(1000)
    max = int(len(allpaintings) // PAGESIZE)
    if len(allpaintings) % PAGESIZE:
      max = max + 1
    if max == 0:
      max = 1
    pages = []
    i = 1
    while i <= max:
      pages.append(str(i))
      i = i + 1

    #Extract the current page number and set the previous page number
    pg = self.request.get("pg")
    if not pg:
      pg = "1"
    prev = int(pg) - 1
    if prev == 0:
      prev = None

    #Use the current page number to fetch the paintings for that page
    bookmark = (int(pg) - 1) * PAGESIZE
    paintings = paintingquery.fetch(PAGESIZE+1, offset=bookmark)

    #If there are more paintings after this page, set the page number for the next page
    next = None
    if len(paintings) == PAGESIZE+1:
      next = int(pg) + 1

    paintings = paintings[:PAGESIZE]
    
    template_values = {
		    'paintings': paintings,
            'pg': pg,
            'max': max,
            'pages': pages,
            'next': next,
            'prev': prev,
            'filter': filter,
            'value': value,
            'order': order,
		    }
    path = os.path.join(os.path.dirname(__file__), 'templates/gallery.html')
    self.response.out.write(template.render(path, template_values))

#The Product class constructs each painting's product page
class Product(webapp.RequestHandler):
  def get(self):
    id = escape(self.request.get('id'))
    query = db.GqlQuery("SELECT * FROM Painting WHERE idnumber = %s" % id)
    painting = query.get()
    template_values = {
		    'painting': painting,
		    }
    path = os.path.join(os.path.dirname(__file__), 'templates/product.html')
    self.response.out.write(template.render(path, template_values))

#Temporary class with dynamically input pricing for the auction
class ProductAuction(webapp.RequestHandler):
  def get(self):
    escape(id = self.request.get('id'))
    query = db.GqlQuery("SELECT * FROM Painting WHERE idnumber = %s" % id)
    painting = query.get()
    template_values = {
		    'painting': painting,
		    }
    path = os.path.join(os.path.dirname(__file__), 'templates/product_auction.html')
    self.response.out.write(template.render(path, template_values))

#The GallerySeries class constructs the 'By Series' page
class GallerySeries(webapp.RequestHandler):
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'templates/series.html')
    self.response.out.write(template.render(path, {}))

#The GallerySize class constructs the 'By Size' page
class GallerySize(webapp.RequestHandler):
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'templates/size.html')
    self.response.out.write(template.render(path, {}))

#The Links class constructs the 'Links' page
class Links(webapp.RequestHandler):
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'templates/links.html')
    self.response.out.write(template.render(path, {}))

#The Contact class constructs the 'Contact' page
class Contact(webapp.RequestHandler):
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'templates/contact.html')
    self.response.out.write(template.render(path, {}))

#The Thumbnails class constructs the 'Thumbnails' page
class Thumbnails(webapp.RequestHandler):
  def get(self):
    paintings = db.GqlQuery("SELECT * FROM Painting ORDER BY idnumber")
    template_values = {
		    'paintings': paintings,
            }
    path = os.path.join(os.path.dirname(__file__), 'templates/thumbnails.html')
    self.response.out.write(template.render(path, template_values))

#This is webapp application constructor for the main site pages, which constructs pages using the classes above based on the URL provided
application = webapp.WSGIApplication ([('/', Home),
				                               ('/index.html', Home),
				                               ('/bio.html', Bio),
				                               ('/inspiration.html', Inspiration),
               				                 ('/gallery', Gallery),
                                       ('/gallery/product', Product),
                                       ('/gallery/auction', ProductAuction),
                                       ('/gallery/series.html', GallerySeries),
                                       ('/gallery/size.html', GallerySize),
				                               ('/links.html', Links),
                                       ('/thumbnails.html', Thumbnails),
				                               ('/contact.html', Contact),],
				                              debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
