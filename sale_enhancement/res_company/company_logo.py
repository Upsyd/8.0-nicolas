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

import os
import re
import openerp
from openerp import SUPERUSER_ID, tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools import image_resize_image


class res_company(osv.osv):
    _inherit = "res.company"

    def _get_logo_website(self, cr, uid, ids, _field_name, _args, context=None):
        result = dict.fromkeys(ids, False)
        for record in self.browse(cr, uid, ids, context=context):
            size = (270, None)
            result[record.id] = image_resize_image(record.partner_id.image, size)
        return result

    _columns ={ 'logo_website': fields.binary("Logo Website"),}


    def write(self, cr, uid, ids, values, context=None):
        self.cache_restart(cr)
        logo_cus = ''
        if values.get('logo'):
            logo_cus = values.get('logo')
            self.pool.get('res.company').write(cr, uid, ids, {'logo_website':logo_cus}, context=context)
        return super(res_company, self).write(cr, uid, ids, values, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
