import jinja2
import os
import webapp2

from google.appengine.ext import db

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


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
class Home(webapp2.RequestHandler):
  def get(self):
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')
    self.response.write(template.render({}))


#The Bio class constructs the Bio page with no template variables
class Bio(webapp2.RequestHandler):
  def get(self):
    template = JINJA_ENVIRONMENT.get_template('templates/bio.html')
    self.response.write(template.render({}))


#The Inspiration class constructs the Inspiration page with no template variables
class Inspiration(webapp2.RequestHandler):
  def get(self):
    template = JINJA_ENVIRONMENT.get_template('templates/inspiration.html')
    self.response.write(template.render({}))


#The Gallery class constructs the Gallery pages based on URL variables
class Gallery(webapp2.RequestHandler):

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
    template = JINJA_ENVIRONMENT.get_template('templates/gallery.html')
    self.response.write(template.render(template_values))


#The Product class constructs each painting's product page
class Product(webapp2.RequestHandler):
  def get(self):
    id = escape(self.request.get('id'))
    query = db.GqlQuery("SELECT * FROM Painting WHERE idnumber = %s" % id)
    painting = query.get()
    template_values = {
            'painting': painting,
    }
    template = JINJA_ENVIRONMENT.get_template('templates/product.html')
    self.response.write(template.render(template_values))


#Temporary class with dynamically input pricing for the auction
class ProductAuction(webapp2.RequestHandler):
  def get(self):
    id = escape(self.request.get('id'))
    query = db.GqlQuery("SELECT * FROM Painting WHERE idnumber = %s" % id)
    painting = query.get()
    template_values = {
            'painting': painting,
    }
    template = JINJA_ENVIRONMENT.get_template('templates/product_auction.html')
    self.response.write(template.render(template_values))


#The GallerySeries class constructs the 'By Series' page
class GallerySeries(webapp2.RequestHandler):
  def get(self):
    template = JINJA_ENVIRONMENT.get_template('templates/series.html')
    self.response.write(template.render({}))


#The GallerySize class constructs the 'By Size' page
class GallerySize(webapp2.RequestHandler):
  def get(self):
    template = JINJA_ENVIRONMENT.get_template('templates/size.html')
    self.response.write(template.render({}))


#The Links class constructs the 'Links' page
class Links(webapp2.RequestHandler):
  def get(self):
    template = JINJA_ENVIRONMENT.get_template('templates/links.html')
    self.response.write(template.render({}))


#The Contact class constructs the 'Contact' page
class Contact(webapp2.RequestHandler):
  def get(self):
    template = JINJA_ENVIRONMENT.get_template('templates/contact.html')
    self.response.write(template.render({}))


#The Thumbnails class constructs the 'Thumbnails' page
class Thumbnails(webapp2.RequestHandler):
  def get(self):
    paintings = db.GqlQuery("SELECT * FROM Painting ORDER BY idnumber")
    template_values = {
            'paintings': paintings,
    }
    template = JINJA_ENVIRONMENT.get_template('templates/thumbnails.html')
    self.response.write(template.render(template_values))


#This is webapp application constructor for the main site pages, which constructs pages using the classes above based on the URL provided
app = webapp2.WSGIApplication ([('/', Home),
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

