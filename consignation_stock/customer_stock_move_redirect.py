# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools import float_compare
from openerp.tools.translate import _
from openerp import tools, SUPERUSER_ID
from openerp.addons.product import _common


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def action_open_window_stock_move(self, cr, uid, ids, context=None):
        mod_obj =self.pool.get('ir.model.data')
        picking_type = self.pool.get('stock.picking.type')
        location_obj = self.pool.get('stock.location')
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'view_move_tree')
        search_view_ref = mod_obj.get_object_reference(cr, uid, 'stock', 'view_move_search')
        view_id = view_ref and view_ref[1] or False
        search_view_id = search_view_ref and search_view_ref[1] or False
        context.update({'search_default_partner_id':ids[0]})
        delivery_ids = picking_type.search(cr,uid,[('code','=','outgoing'),('name','=','Delivery Orders')],context=context)
        if delivery_ids:
            context.update({'search_default_picking_type_id':delivery_ids[0]})
        location_id = location_obj.search(cr,uid,[('name','=','Stock Consignation'),('location_id','=',10)],context=context)
        if location_id:
            context.update({'search_default_location_dest_id':location_id[0]})
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.move',
            'res_id': ids[0],
            #'view_id': view_id,
            'search_view_id': search_view_id,
            'target': 'current',
            'nodestroy': True,
            'context': context,
              }



class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'partner_id': fields.related('picking_id', 'partner_id', type='many2one', relation='res.partner', store=True, string='Customer'),
}

class product_template(osv.osv):
    _inherit = 'product.template'
    _columns = {
        'consignation_location_id': fields.many2one('stock.location','Consignation Location'),
}

class procurement_order(osv.osv):
    _inherit = "procurement.order"

    def _run_move_create(self, cr, uid, procurement, context=None):
        vals = super(procurement_order, self)._run_move_create(cr, uid, procurement, context=context)
        print "resssssssssssssss",vals
        location_dest_id = False
        if procurement.product_id:
            if procurement.product_id.product_tmpl_id:
                if procurement.product_id.product_tmpl_id.consignation_location_id:
                    location_dest_id = procurement.product_id.product_tmpl_id.consignation_location_id and procurement.product_id.product_tmpl_id.consignation_location_id.id or False
                else:
                    location_dest_id = procurement.location_id.id
        print "\n\n before updateeeeeeeee",vals
        vals.update({'location_dest_id': location_dest_id})
        print "\n\n after update valssssssssss",vals
        return vals

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
