from functools import update_wrapper
from django.conf.urls import url
from django.http import HttpResponse
from tastypie import http
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.resources import ModelResource, convert_post_to_put
from nested_resource import utils
from tastypie.utils import trailing_slash


class NestedMixin(object):

    """
    A tastypie resource mixin that allows you to make any resource nested within
    another resource.
    """

    def get_nested_resource(self, resource_cls, parent_attr):
        resource = utils.import_class(resource_cls)()

        url_pattern = r"^(?P<parent_resource_name>%s)/(?P<%s>.*?)/" \
                      r"(?P<resource_name>%s)%s$" % \
                      (self._meta.resource_name, parent_attr,
                       resource._meta.resource_name, trailing_slash())

        return url(url_pattern, resource.wrap_view('nested_dispatch_list'),
                   name="api_%s_dispatch_list" % resource._meta.resource_name)

    def nested_dispatch_list(self, request, **kwargs):
        """
        Handles the common operations (allowed HTTP method, authentication,
        throttling, method lookup) surrounding most CRUD interactions.
        """
        allowed_methods = self._meta.nested_allowed_methods

        if 'HTTP_X_HTTP_METHOD_OVERRIDE' in request.META:
            request.method = request.META['HTTP_X_HTTP_METHOD_OVERRIDE']

        request_method = self.method_check(request, allowed=allowed_methods)
        method = getattr(self, "%s_list" % request_method, None)

        if method is None:
            raise ImmediateHttpResponse(response=http.HttpNotImplemented())

        self.is_authenticated(request)
        self.throttle_check(request)

        # All clear. Process the request.
        request = convert_post_to_put(request)
        response = method(request, **kwargs)

        # Add the throttled request.
        self.log_throttled_access(request)

        # If what comes back isn't a ``HttpResponse``, assume that the
        # request was accepted and that some action occurred. This also
        # prevents Django from freaking out.
        if not isinstance(response, HttpResponse):
            return http.HttpNoContent()

        return response

    def add_nested_custom_api(self, resource_cls, parent_attr,
                              urlpattern, view, api_name=None):

        resource = utils.import_class(resource_cls)()

        api_name = api_name or view

        urlpattern = r"^(?P<parent_resource_name>%s)/(?P<%s>.*?)/" \
                     r"(?P<resource_name>%s)/%s%s$" %\
                     (self._meta.resource_name, parent_attr,
                      resource._meta.resource_name,
                      urlpattern, trailing_slash())

        return url(urlpattern, resource.wrap_view(view), api_name)
