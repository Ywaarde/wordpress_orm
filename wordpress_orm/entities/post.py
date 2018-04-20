                                                                                                                                                                                                                                                                                                                                                                                                                                                       
'''

WordPress API reference: https://developer.wordpress.org/rest-api/reference/posts/
'''

import json
import logging
import requests
from datetime import datetime

from .wordpress_entity import WPEntity, WPRequest, context_values
from .user import User
from .category import Category
from .. import exc

logger = logging.getLogger("{}".format(__loader__.name.split(".")[0])) # package name

order_values = ["asc", "desc"]
orderby_values = ["author", "date", "id", "include", "modified", "parent",
				  "relevance", "slug", "title"]

class Post(WPEntity):

	def __init__(self, id=None, session=None, api=None):
		super().__init__(api=api)
			
	def __repr__(self):
		if len(self.s.title) < 11:
			truncated_title = self.s.title
		else:
			truncated_title = self.s.title[0:10] + "..."
		return "<WP {0} object at {1}, id={2}, title='{3}'>".format(self.__class__.__name__,
													 hex(id(self)), self.s.id, truncated_title)

	@property
	def schema_fields(self):
		return ["date", "date_gmt", "guid", "id", "link", "modified", "modified_gmt",
			   "slug", "status", "type", "password", "title", "content", "author",
			   "excerpt", "featured_media", "comment_status", "ping_status", "format",
			   "meta", "sticky", "template", "categories", "tags"]

	@property
	def featured_media(self):
		'''
		Returns the 'Media' object that is the "featured media" for this post.
		'''
		mr = self.api.MediaRequest()
		mr.id = self.s.featured_media
		media_list = mr.get()
		if len(media_list) == 1:
			return media_list[0]
		else:
			return None
			
	@property
	def author(self):
		'''
		Returns the author of this post, class: 'User'.
		'''
		ur = self.api.UserRequest()
		ur.id = self.s.author # ID for the author of the object
		user_list = ur.get()
		if len(user_list) == 1:
			return user_list[0]
		else:
			raise exc.UserNotFound("User ID '{0}' not found.".format(self.author))
	
	@property
	def comments(self):
		'''
		Returns the comments associated with this post.
		'''
		return self.api.CommentRequest(post=self).get()

class PostRequest(WPRequest):
	'''
	A class that encapsulates requests for WordPress posts.
	'''		
	def __init__(self, api=None, categories=None, slugs=None):		
		super().__init__(api=api)
		self.id = None # WordPress ID
		
		# parameters that undergo validation, i.e. need custom setter
		#self._author = None
		self._after = None
		self._before = None
		self._order = None
		self._orderby = None
		
		self._status = list()
		self._author_ids = list()
		self._category_ids = list()
		self._slugs = list()
		
		if categories:
			self.categories = categories
		if slugs:
			self.slugs = slugs
		
	@property
	def parameter_names(self):
		'''
		'''
		return ["context", "page", "per_page", "search", "after", "author",
				"author_exclude", "before", "exclude", "include", "offset",
				"order", "orderby", "slug", "status", "categories",
				"categories_exclude", "tags", "tags_exclude", "sticky"]

	def get(self):
		'''
		Returns a list of 'Post' objects that match the parameters set in this object.
		'''
		self.url = self.api.base_url + "posts"
		
		if self.id:
			self.url += "/{}".format(self.id)

		# -------------------
		# populate parameters
		# -------------------
		if self.context:
			self.parameters["context"] = self.context
			request_context = self.context
		else:
			request_context = "view" # default value
			
		if self.page:
			self.parameters["page"] = self.page
		
		if self.per_page:
			self.parameters["per_page"] = self.per_page

		if self.search:
			self.parameters["search"] = self.search
			
		if self.after:
			self.parameters["after"] = self._after.isoformat()

		if len(self.author) > 0:
			# takes a list of author IDs
			self.parameters["author"] = ",".join(self.author)
		
		if len(self.status) > 0:
			self.parameters["status"] = ",".join(self.status)
			
		if self.slug:
			self.parameters["slug"] = self.slug
		
		if len(self.categories) > 0:
			self.parameters["categories"] = ",".join(self._category_ids)
		
		if self.order:
			self.parameters["order"] = self.order
					
		# -------------------

		try:
			self.get_response()
			logger.debug("URL='{}'".format(self.request.url))
		except requests.exceptions.HTTPError:
			logger.debug("Post response code: {}".format(self.response.status_code))
			if self.response.status_code == 400: # bad request
				logger.debug("URL={}".format(self.response.url))
				raise exc.BadRequest("400: Bad request. Error: \n{0}".format(json.dumps(self.response.json(), indent=4)))
			elif self.response.status_code == 404: # not found
				return None
			
		posts_data = self.response.json()

		if isinstance(posts_data, dict):
			# only one object was returned; make it a list
			posts_data = [posts_data]
	
		posts = list()
		for d in posts_data:
			post = Post(api=self.api)
			post.json = d
			
			# Properties applicable to 'view', 'edit', 'embed' query contexts
			#
			post.s.date = d["date"]
			post.s.id = d["id"]
			post.s.link = d["link"]
			post.s.slug = d["slug"]
			post.s.type = d["type"]
			post.s.author = d["author"]
			post.s.excerpt = d["excerpt"]["rendered"]
			post.s.featured_media = d["featured_media"]
			
			# Properties applicable to only 'view', 'edit' query contexts:
			#
			if request_context in ["view", "edit"]:
				view_edit_properties = ["date_gmt", "guid", "modified", "modified_gmt", "status",
										"content", "comment_status", "ping_status", "format", "meta",
										"sticky", "template", "categories", "tags"]
				for key in view_edit_properties:
					setattr(post, key, d[key])
#				post.s.date_gmt = d["date_gmt"]
#				post.s.guid = d["guid"]
#				post.s.modified = d["modified"]
#				post.s.modified_gmt = d["modified_gmt"]
#				post.s.status = d["status"]
#				post.s.content = d["content"]
#				post.s.comment_status = d["comment_status"]
#				post.s.ping_status = d["ping_status"]
#				post.s.format = d["format"]
#				post.s.meta = d["meta"]
#				post.s.sticky = d["sticky"]
#				post.s.template = d["template"]
#				post.s.categories = d["categories"]
#				post.s.tags = d["tags"]
				
			# Properties applicable to only 'edit' query contexts
			#
			if request_context in ['edit']:
				post.s.password = d["password"]
			
			# Properties applicable to only 'view' query contexts
			#
			print(d["title"])
			if request_context == 'view':
				post.s.title = d["title"]["rendered"]
			else:
				# not sure what the returned 'title' object looks like
				logger.debug(d)
				logger.debug(d["title"])
				logger.debug(request_context)
				raise NotImplementedError
			
			posts.append(post)
			
		return posts
	
	@property
	def context(self):
		if self._context is None:
			self._context = None
		return self._context
	
	@context.setter
	def context(self, value):
		if value is None:
			self.parameters.pop("context", None)
			self._context =  None
			return
		else:
			try:
				value = value.lower()
				if value in ["view", "embed", "edit"]:
					self._context = value
					return
			except:
				pass
			raise ValueError ("'context' may only be one of ['view', 'embed', 'edit']")
	
	@property
	def author(self):
		#return self._author
		#return self.parameters.get("author", None)
		return self._author_ids
		
	@author.setter
	def author(self, value):
		'''
		Set author parameter for this request; stores WordPress user ID.
		'''
		author_id = None
		
		if value is None:
			self.parameters.pop("author", None) # remove key
			return
			#self.g = None

		elif isinstance(value, User):
			# a single user was given, replace any existing list with this one
			self._author_ids = list()
			author_id = value.s.id

		elif isinstance(value, int):
			# a single id was given, replace any existing list with this one
			self._author_ids = list()
			author_id = value # assuming WordPress ID
			#self.parameters["author"] = value
			#self._author = value

		elif isinstance(value, str):
			# is this string value the WordPress user ID?
			try:
				author_id = int(value)
			except ValueError:
				# nope, see if it's the username and get the User object
				try:
					user = self.api.user(username=value)
					author_id = user.s.id
				except exc.NoEntityFound:
					raise ValueError("Could not determine a user from the value: {0} (type {1})".format(value, type(value)))
							
		else:
			raise ValueError("Unexpected value type passed to 'author' (type: '{1}')".format(type(value)))
		
		assert author_id is not None, "could not determine author_id from value {0}".format(value)
		#self.parameters["author"].append(str(author_id))
		self._author_ids.append(author_id)

	@property
	def after(self):
		'''
		WordPress parameter to return posts after this date.
		'''
		return self._after
	
	@after.setter
	def after(self, value):
		'''
		Set the WordPress parameter to return posts after this date.
		'''
		# The stored format is a datetime object, even though WordPress requires
		# it to be ISO-8601.
		#
		if value is None:
			self.parameters.pop("after", None)
			self._after = None
		elif isinstance(value, datetime):
			self._after = value
		else:
			raise ValueError("Th 'after' property only accepts `datetime` objects.")

	@property
	def before(self):
		'''
		WordPress parameter to return posts before this date.
		'''
		return self._after
	
	@after.setter
	def before(self, value):
		'''
		Set the WordPress parameter to return posts before this date.
		'''
		# The stored format is a datetime object, even though WordPress requires
		# it to be ISO-8601.
		#
		if value is None:
			self.parameters.pop("before", None)
			self._before = None
		elif isinstance(value, datetime):
			self._before = value
		else:
			raise ValueError("The 'before' property only accepts `datetime` objects.")

	@property
	def order(self):
		return self._order;
		#return self.api_params.get('order', None)
		
	@order.setter
	def order(self, value):
		if value is None:
			self.parameters.pop("order", None)
			self._order = None
		else:
			if isinstance(value, str):
				value = value.lower()
				if value not in order_values:
					raise ValueError('The "order" parameter must be one '+\
									 'of these values: {}'.format(order_values))
				else:
					#self.api_params['order'] = value
					self._order = value
			else:
				raise ValueError('The "order" parameter must be one of '+\
								 'these values: {} (or None).'.format(order_values))
		return self._order

	@property
	def orderby(self):
		return self.api_params.get('orderby', None)
		
	@orderby.setter
	def orderby(self, value):
		if value is None:
			self.parameters.pop("orderby", None)
			self._orderby = None
		else:
			if isinstance(value, str):
				value = value.lower()
				if value not in orderby_values:
					raise ValueError('The "orderby" parameter must be one '+\
									 'of these values: {}'.format(orderby_values))
				else:
					#self.api_params['orderby'] = value
					self._orderby = value
			else:
				raise ValueError('The "orderby" parameter must be one of these '+\
								 'values: {} (or None).'.format(orderby_values))
		return self._orderby

	@property
	def status(self):
		return self._status
	
	@status.setter
	def status(self, value):
		'''
		
		Note that 'status' may contain one or more values.
		Ref: https://developer.wordpress.org/rest-api/reference/posts/#arguments
		'''
		if value is None:
			self.parameters.pop("status", None)
			self._status = list() # set default value
			return
		try:
			value = value.lower()
			if value in ["draft", "pending", "private", "publish", "future"]:
				# may be one or more values; store as a list
				if self._status:
					self._status.append(value)
				else:
					self._status = [value]
				return
		except:
			pass
		raise ValueError("'status' must be one of ['draft', 'pending', 'private', 'publish', 'future'] ('{0}' given)".format(value))
		
	@property
	def categories(self):
		return self._category_ids

	@categories.setter
	def categories(self, values):
		'''
		This method validates the categories passed to this request.
		
		It accepts category ID (integer or string) or the slug value.
		'''
		if values is None:
			self.parameters.pop("categories", None)
			self._category_ids = list()
			return
		elif not isinstance(values, list):
			raise ValueError("Categories must be provided as a list (or append to the existing list).")
		
		for c in values:
			cat_id = None
			if isinstance(c, Category):
				cat_id = c.s.id
#				self._category_ids.append(str(c.s.id))
			elif isinstance(c, int):
#				self._category_ids.append(str(c))
				cat_id = c
			elif isinstance(c, str):
				try:
					# is this a category ID value?
					cat_id = int(c)
					#self._category_ids.append(str(int(c)))
				except ValueError:
					# not a category ID value, try by slug?
					try:
						category = self.api.category(slug=c)
						cat_id = category.s.id
						#self._category_ids.append(category.s.id)
					except exc.NoEntityFound:
						logger.debug("Asked to find a category with the slug '{0}' but not found.".format(slug))
			
			# Categories are stored as string ID values.
			#
			self._category_ids.append(str(cat_id))

	@property
	def slugs(self):
		'''
		The list of post slugs to retrieve.
		'''
		return self._slugs
		
	@slugs.setter
	def slugs(self, values):
		if values is None:
			self.parameters.pop("slugs", None)
			self._slugs = list()
			return
		elif not isinstance(values, list):
			raise ValueError("Slugs must be provided as a list (or append to the existing list).")
		
		for s in values:
			if isinstance(s, str):
				self._slugs.append(s)
			else:
				raise ValueError("Unexpected type for property list 'slugs'; expected str, got '{0}'".format(type(s)))






















