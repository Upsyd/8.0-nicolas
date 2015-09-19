# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C) 2014-Today BrowseInfo (<http://www.browseinfo.in>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
{
    'name': 'Sale Enhancement',
    'category': 'Customization',
    'summary': 'Sale enhancement',
    'version': '1.0',
    'description': """
        """,
    'author': 'BrowseInfo',
    'website': 'www.browseinfo.in',
    'depends': ['base','product','sale','website','website_sale'],
    'data': [
             'views/templates.xml',
             'views/multi_product_images.xml',
             'security/ir.model.access.csv',
             ],
    'qweb' : [ "static/src/xml/*.xml" ],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
