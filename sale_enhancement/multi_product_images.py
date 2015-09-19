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

from openerp.osv import osv, fields

class product_image(osv.osv):
    _name = 'product.image'

    _columns = {
        'name': fields.char('Name'),
        'description': fields.text('Description'),
        'image_alt': fields.text('Image Label'),
        'image': fields.binary('Image'),
        'image_small': fields.binary('Image Small'),
        'product_tmpl_id': fields.many2one('product.template', 'Product'),
    }

class product_product(osv.osv):
    _inherit = 'product.product'

    _columns = {
        'images': fields.related('product_tmpl_id', 'images', type="one2many", relation="product.image", string='Images', store=False),
    }

class product_template(osv.osv):
    _inherit = 'product.template'

    _columns = {
        'images': fields.one2many('product.image', 'product_tmpl_id', string='Images'),
    }

class product_pricelist_item(osv.osv):
    _inherit = "product.pricelist.item"

    _columns = {
        'product_public_categ_id': fields.many2one('product.public.category', 'Product Public Category', ondelete='cascade'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
