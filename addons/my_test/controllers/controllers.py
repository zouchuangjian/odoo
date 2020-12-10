# -*- coding: utf-8 -*-
from odoo import http


class MyTest(http.Controller):
    @http.route('/my_test/my_test/', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/my_test/my_test/objects/', auth='public')
    def list(self, **kw):
        return http.request.render('my_test.listing', {
            'root': '/my_test/my_test',
            'objects': http.request.env['my_test.my_test'].search([]),
        })

    @http.route('/my_test/my_test/objects/<model("my_test.my_test"):obj>/', auth='public')
    def object(self, obj, **kw):
        return http.request.render('my_test.object', {
            'object': obj
        })
