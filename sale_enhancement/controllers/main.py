# -*- coding: utf-8 -*-
import werkzeug
import functools
from cStringIO import StringIO
import openerp

from openerp.modules import get_module_resource
from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug

PPG = 20 # Products Per Page
PPR = 4  # Products Per Row

class table_compute(object):
    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx+x>=PPR:
                    res = False
                    break
                row = self.table.setdefault(posy+y, {})
                if row.setdefault(posx+x) is not None:
                    res = False
                    break
            for x in range(PPR):
                self.table[posy+y].setdefault(x, None)
        return res

    def process(self, products):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        for p in products:
            x = min(max(p.website_size_x, 1), PPR)
            y = min(max(p.website_size_y, 1), PPR)
            if index>=PPG:
                x = y = 1

            pos = minpos
            while not self._check_place(pos%PPR, pos/PPR, x, y):
                pos += 1
            # if 21st products (index 20) and the last line is full (PPR products in it), break
            # (pos + 1.0) / PPR is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= PPG and ((pos + 1.0) / PPR) > maxy:
                break

            if x==1 and y==1:   # simple heuristic for CPU optimization
                minpos = pos/PPR

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos/PPR)+y2][(pos%PPR)+x2] = False
            self.table[pos/PPR][pos%PPR] = {
                'product': p, 'x':x, 'y': y,
                'class': " ".join(map(lambda x: x.html_class or '', p.website_style_ids))
            }
            if index<=PPG:
                maxy=max(maxy,y+(pos/PPR))
            index += 1

        # Format table according to HTML needs
        rows = self.table.items()
        rows.sort()
        rows = map(lambda x: x[1], rows)
        for col in range(len(rows)):
            cols = rows[col].items()
            cols.sort()
            x += len(cols)
            rows[col] = [c for c in map(lambda x: x[1], cols) if c != False]

        return rows

        # TODO keep with input type hidden


class QueryURL(object):
    def __init__(self, path='', **args):
        self.path = path
        self.args = args

    def __call__(self, path=None, **kw):
        if not path:
            path = self.path
        for k,v in self.args.items():
            kw.setdefault(k,v)
        l = []
        for k,v in kw.items():
            if v:
                if isinstance(v, list) or isinstance(v, set):
                    l.append(werkzeug.url_encode([(k,i) for i in v]))
                else:
                    l.append(werkzeug.url_encode([(k,v)]))
        if l:
            path += '?' + '&'.join(l)
        return path


def get_pricelist():
    cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
    sale_order = context.get('sale_order')
    if sale_order:
        pricelist = sale_order.pricelist_id
    else:
        partner = pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context).partner_id
        pricelist = partner.property_product_pricelist
    return pricelist

def internal_categories():
    cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
    internal_categ_obj = pool.get('product.category')
    internal_categ_ids = internal_categ_obj.search(request.cr, request.uid, [], context=request.context)
    internal_categories = internal_categ_obj.browse(request.cr, request.uid, internal_categ_ids, context=request.context)
    internal_categs = filter(lambda x: not x.parent_id, internal_categories)
    return internal_categs

class sale_enhancement(http.Controller):

    def get_pricelist(self):
        return get_pricelist()

    def internal_categories(self):
        return internal_categories()

    def get_attribute_value_ids(self, product):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        currency_obj = pool['res.currency']
        attribute_value_ids = []
        if request.website.pricelist_id.id != context['pricelist']:
            website_currency_id = request.website.currency_id.id
            currency_id = self.get_pricelist().currency_id.id
            for p in product.product_variant_ids:
                price = currency_obj.compute(cr, uid, website_currency_id, currency_id, p.lst_price)
                attribute_value_ids.append([p.id, [v.id for v in p.attribute_value_ids if len(v.attribute_id.value_ids) > 1], p.price, price])
        else:
            attribute_value_ids = [[p.id, [v.id for v in p.attribute_value_ids if len(v.attribute_id.value_ids) > 1], p.price, p.lst_price]
                for p in product.product_variant_ids]

        return attribute_value_ids

    @http.route([
        '/shop/home',
    ], type='http', auth="public", website=True)
    def home(self, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        domain = request.website.sale_product_domain()

        product_obj = pool.get('product.template')

        url = "/shop/home"
        keep = QueryURL('/shop')
        # added code
        internal_categs = self.internal_categories()

        #code for not list out categories which has no product
        all_prod_ids = product_obj.search(cr, uid, [], context=context)
        all_prod = product_obj.browse(cr, uid, all_prod_ids, context=context)
        all_pids = []
        for pids in all_prod:
            if pids['public_categ_ids']:
                all_pids.append(pids['public_categ_ids'].id)
                if pids['public_categ_ids'].parent_id:
                    all_pids.append(pids['public_categ_ids'].parent_id.id)
        if all_pids:
            all_pids = list(set(all_pids))

        category_obj = pool['product.public.category']
        categories = category_obj.browse(cr, uid, all_pids, context=context)

        #code for not list out sub categories which has no product
        sub_categories = filter(lambda x: x.parent_id, categories)
        sub_categ = []
        for sc in sub_categories:
            sub_categ.append(sc.id)

        values = {
            'categories': filter(lambda x: not x.parent_id, categories),
            'sub_categ' : sub_categ,
            'int_categories': internal_categs,
            'keep': keep,
        }
        return request.website.render("sale_enhancement.shop_home", values)

    @http.route([
        '/shop/category/<string:id>/<model("product.category"):category>',
        '/shop/category/<string:id>/<model("product.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def product_shop(self, category=None, id=None, page=0, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        domain = request.website.sale_product_domain()

        if search:
            args_id = id.split('-')
            if len(args_id) > 1:
                domain += ['|', '|', '|', ('name', 'ilike', search), ('description', 'ilike', search),
                           ('description_sale', 'ilike', search), ('product_variant_ids.default_code', 'ilike', search), ('product_variant_ids.public_categ_ids', 'child_of', int(args_id[-1]))]
            else:
                domain += ['|', '|', '|', ('name', 'ilike', search), ('description', 'ilike', search),
                           ('description_sale', 'ilike', search), ('product_variant_ids.default_code', 'ilike', search)]

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_line_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domain += [('attribute_line_ids.value_ids', 'in', ids)]

        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list)

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        product_obj = pool.get('product.template')

        #domain code for products
        pdomain = list(domain)
        if category:
            args_id = id.split('-')
            if len(args_id) > 1:
                pdomain.append(('product_variant_ids.public_categ_ids', 'child_of', int(args_id[-1])))
                pdomain.append(('categ_id','child_of', category.id))
            else:
                pdomain.append(('categ_id','child_of',int(id)))

        url = "/shop"
        product_count = product_obj.search_count(cr, uid, pdomain, context=context)
        if search:
            post["search"] = search
        if category:
            category = pool['product.category'].browse(cr, uid, int(category), context=context)
            url = "/shop/category/%s" % slug(category)
        if id:
            url = "/shop/category/%s/%s" % (id, slug(category))

        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        product_ids = product_obj.search(cr, uid, pdomain, limit=PPG, offset=pager['offset'], order='website_published desc, website_sequence desc', context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)

        #code for not list out categories which has no product and shows all categories
        pdom = [('sale_ok', '=', True), ('categ_id','child_of',category.id)]
        all_prod_ids = product_obj.search(cr, uid, pdom, context=context)
        all_prod = product_obj.browse(cr, uid, all_prod_ids, context=context)
        all_pids = []
        for pids in all_prod:
            if pids['public_categ_ids']:
                all_pids.append(pids['public_categ_ids'].id)
                if pids['public_categ_ids'].parent_id:
                    all_pids.append(pids['public_categ_ids'].parent_id.id)
        if all_pids:
            all_pids = list(set(all_pids))

        # added code
        internal_categs = self.internal_categories()

        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [], context=context)
        styles = style_obj.browse(cr, uid, style_ids, context=context)

        category_obj = pool['product.public.category']
        categories = category_obj.browse(cr, uid, all_pids, context=context)

        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        ## breadcrumb code
        main_categ = None
        if len(args_id) > 1:
            ids = int(args_id[-1])
            main_categ = category_obj.browse(request.cr, request.uid, [ids], context=request.context)[0]
            all_categ_ids = category_obj.search(request.cr, request.uid, [], context=request.context)
            all_categ = category_obj.browse(request.cr, request.uid, all_categ_ids, context=request.context)
            bread_crumb = set()
            for categs in all_categ:
                if categs == main_categ:
                    parent = categs.parent_id
                    while parent:
                        bread_crumb.add(parent)
                        parent = parent.parent_id
            bread_crumb = list(bread_crumb)
            bread_crumb.sort(key=lambda x: x.id)
        else:
            all_categ_ids = category_obj.search(request.cr, request.uid, [], context=request.context)
            all_categ = category_obj.browse(request.cr, request.uid, all_categ_ids, context=request.context)
            bread_crumb = set()
            for categs in all_categ:
                if categs == category:
                    parent = category.parent_id
                    while parent:
                        bread_crumb.add(parent)
                        parent = parent.parent_id
            bread_crumb = list(bread_crumb)
            bread_crumb.sort(key=lambda x: x.id)

        #code for not list out categories which has no product
        sub_categories = filter(lambda x: x.parent_id, categories)
        sub_categ = []
        for sc in sub_categories:
            sub_categ.append(sc.id)

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'bins': table_compute().process(products),
            'rows': PPR,
            'b_crumb': bread_crumb,
            'main_categ': main_categ,
            'styles': styles,
            'sub_categ' : sub_categ,
            'categories': filter(lambda x: not x.parent_id, categories),
            'int_categories': internal_categs,
            'id':id,
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
        }
        return request.website.render("website_sale.products", values)


    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True)
    def shop(self, category=None, id=None, page=0, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        domain = request.website.sale_product_domain()

        if search:
            domain += ['|', '|', '|', ('name', 'ilike', search), ('description', 'ilike', search),
                ('description_sale', 'ilike', search), ('product_variant_ids.default_code', 'ilike', search)]
        if category:
            domain += [('public_categ_ids', 'child_of', int(category))]

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_line_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domain += [('attribute_line_ids.value_ids', 'in', ids)]

        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list)

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)

        product_obj = pool.get('product.template')

        url = "/shop"
        product_count = product_obj.search_count(cr, uid, domain, context=context)
        if search:
            post["search"] = search
        if category:
            category = pool['product.public.category'].browse(cr, uid, int(category), context=context)
            url = "/shop/category/%s" % slug(category)

        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order='website_published desc, website_sequence desc', context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)

        #code for not list out categories which has no product
        all_prod_ids = product_obj.search(cr, uid, [], context=context)
        all_prod = product_obj.browse(cr, uid, all_prod_ids, context=context)
        all_pids = []
        for pids in all_prod:
            if pids['public_categ_ids']:
                all_pids.append(pids['public_categ_ids'].id)
                if pids['public_categ_ids'].parent_id:
                    all_pids.append(pids['public_categ_ids'].parent_id.id)
        if all_pids:
            all_pids = list(set(all_pids))

        # added code
        internal_categs = self.internal_categories()

        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [], context=context)
        styles = style_obj.browse(cr, uid, style_ids, context=context)

        category_obj = pool['product.public.category']
        categories = category_obj.browse(cr, uid, all_pids, context=context)

        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        ## breadcrumb code
        all_categ_ids = category_obj.search(request.cr, request.uid, [], context=request.context)
        all_categ = category_obj.browse(request.cr, request.uid, all_categ_ids, context=request.context)
        bread_crumb = set()
        for categs in all_categ:
            if categs == category:
                parent = category.parent_id
                while parent:
                    bread_crumb.add(parent)
                    parent = parent.parent_id
        bread_crumb = list(bread_crumb)
        bread_crumb.sort(key=lambda x: x.id)

        #code for not list out sub categories which has no product
        sub_categories = filter(lambda x: x.parent_id, categories)
        sub_categ = []
        for sc in sub_categories:
            sub_categ.append(sc.id)

        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'bins': table_compute().process(products),
            'rows': PPR,
            'b_crumb': bread_crumb,
            'styles': styles,
            'categories': filter(lambda x: not x.parent_id, categories),
            'sub_categ' : sub_categ,
            'int_categories': internal_categs,
            'id':id,
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
        }
        return request.website.render("website_sale.products", values)

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, search='', category='', **kwargs):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        category_obj = pool['product.public.category']
        template_obj = pool['product.template']

        context.update(active_id=product.id)

        if category:
            category = category_obj.browse(cr, uid, int(category), context=context)

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])

        keep = QueryURL('/shop', category=category and category.id, search=search, attrib=attrib_list)

        internal_categs = self.internal_categories()

        #code for not list out categories which has no product
        all_prod_ids = template_obj.search(cr, uid, [], context=context)
        all_prod = template_obj.browse(cr, uid, all_prod_ids, context=context)
        all_pids = []
        for pids in all_prod:
            if pids['public_categ_ids']:
                all_pids.append(pids['public_categ_ids'].id)
                print "#############", pids['public_categ_ids']
                if pids['public_categ_ids'].parent_id:
                    all_pids.append(pids['public_categ_ids'].parent_id.id)
        if all_pids:
            all_pids = list(set(all_pids))

        categories = category_obj.browse(cr, uid, all_pids, context=context)
        category_ids = category_obj.search(cr, uid, [], context=context)
        category_list = category_obj.name_get(cr, uid, category_ids, context=context)
        category_list = sorted(category_list, key=lambda category: category[1])

        pricelist = self.get_pricelist()

        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)

        if not context.get('pricelist'):
            context['pricelist'] = int(self.get_pricelist())
            product = template_obj.browse(cr, uid, int(product), context=context)

        #code for not list out categories which has no product
        sub_categories = filter(lambda x: x.parent_id, categories)
        sub_categ = []
        for sc in sub_categories:
            sub_categ.append(sc.id)

        values = {
            'search': search,
            'category': category,
            'product': product,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'int_categories': internal_categs, # added this code
            'compute_currency': compute_currency,
            'attrib_set': attrib_set,
            'keep': keep,
            'category_list': category_list,
            'main_object': product,
            'get_attribute_value_ids': self.get_attribute_value_ids,
            'categories': filter(lambda x: not x.parent_id, categories), # added this code
            'sub_categ' : sub_categ, # added this code
        }
        return request.website.render("website_sale.product", values)

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        order = request.website.sale_get_order()
        if order:
            from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
            to_currency = order.pricelist_id.currency_id
            compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)
        else:
            compute_currency = lambda price: price

        internal_categs = self.internal_categories()

        values = {
            'order': order,
            'int_categories': internal_categs,
            'compute_currency': compute_currency,
            'suggested_products': [],
        }
        if order:
            _order = order
            if not context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()

        return request.website.render("website_sale.cart", values)

    def checkout_redirection(self, order):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        # must have a draft sale order with lines at this point, otherwise reset
        if not order or order.state != 'draft':
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/shop')

        # if transaction pending / done: redirect to confirmation
        tx = context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

    mandatory_billing_fields = ["name", "phone", "email", "street2", "city", "country_id"]
    optional_billing_fields = ["street", "state_id", "vat", "vat_subjected", "zip"]
    mandatory_shipping_fields = ["name", "phone", "street", "city", "country_id"]
    optional_shipping_fields = ["state_id", "zip"]

    def checkout_parse(self, address_type, data, remove_prefix=False):
        """ data is a dict OR a partner browse record
        """
        # set mandatory and optional fields
        assert address_type in ('billing', 'shipping')
        if address_type == 'billing':
            all_fields = self.mandatory_billing_fields + self.optional_billing_fields
            prefix = ''
        else:
            all_fields = self.mandatory_shipping_fields + self.optional_shipping_fields
            prefix = 'shipping_'

        # set data
        if isinstance(data, dict):
            query = dict((prefix + field_name, data[prefix + field_name])
                for field_name in all_fields if data.get(prefix + field_name))
        else:
            query = dict((prefix + field_name, getattr(data, field_name))
                for field_name in all_fields if getattr(data, field_name))
            if address_type == 'billing' and data.parent_id:
                query[prefix + 'street'] = data.parent_id.name

        if query.get(prefix + 'state_id'):
            query[prefix + 'state_id'] = int(query[prefix + 'state_id'])
        if query.get(prefix + 'country_id'):
            query[prefix + 'country_id'] = int(query[prefix + 'country_id'])

        if query.get(prefix + 'vat'):
            query[prefix + 'vat_subjected'] = True

        if not remove_prefix:
            return query

        return dict((field_name, data[prefix + field_name]) for field_name in all_fields if data.get(prefix + field_name))

    def checkout_values(self, data=None):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
        orm_partner = registry.get('res.partner')
        orm_user = registry.get('res.users')
        orm_country = registry.get('res.country')
        state_orm = registry.get('res.country.state')

        country_ids = orm_country.search(cr, SUPERUSER_ID, [], context=context)
        countries = orm_country.browse(cr, SUPERUSER_ID, country_ids, context)
        states_ids = state_orm.search(cr, SUPERUSER_ID, [], context=context)
        states = state_orm.browse(cr, SUPERUSER_ID, states_ids, context)
        partner = orm_user.browse(cr, SUPERUSER_ID, request.uid, context).partner_id

        order = None

        shipping_id = None
        shipping_ids = []
        checkout = {}
        if not data:
            if request.uid != request.website.user_id.id:
                checkout.update( self.checkout_parse("billing", partner) )
                shipping_ids = orm_partner.search(cr, SUPERUSER_ID, [("parent_id", "=", partner.id), ('type', "=", 'delivery')], context=context)
            else:
                order = request.website.sale_get_order(force_create=1, context=context)
                if order.partner_id:
                    domain = [("partner_id", "=", order.partner_id.id)]
                    user_ids = request.registry['res.users'].search(cr, SUPERUSER_ID, domain, context=dict(context or {}, active_test=False))
                    if not user_ids or request.website.user_id.id not in user_ids:
                        checkout.update( self.checkout_parse("billing", order.partner_id) )
        else:
            checkout = self.checkout_parse('billing', data)
            try:
                shipping_id = int(data["shipping_id"])
            except ValueError:
                pass
            if shipping_id == -1:
                checkout.update(self.checkout_parse('shipping', data))

        if shipping_id is None:
            if not order:
                order = request.website.sale_get_order(context=context)
            if order and order.partner_shipping_id:
                shipping_id = order.partner_shipping_id.id

        shipping_ids = list(set(shipping_ids) - set([partner.id]))

        if shipping_id == partner.id:
            shipping_id = 0
        elif shipping_id > 0 and shipping_id not in shipping_ids:
            shipping_ids.append(shipping_id)
        elif shipping_id is None and shipping_ids:
            shipping_id = shipping_ids[0]

        ctx = dict(context, show_address=1)
        shippings = []
        if shipping_ids:
            shippings = shipping_ids and orm_partner.browse(cr, SUPERUSER_ID, list(shipping_ids), ctx) or []
        if shipping_id > 0:
            shipping = orm_partner.browse(cr, SUPERUSER_ID, shipping_id, ctx)
            checkout.update( self.checkout_parse("shipping", shipping) )

        checkout['shipping_id'] = shipping_id

        # Default search by user country
        if not checkout.get('country_id'):
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                country_ids = request.registry.get('res.country').search(cr, uid, [('code', '=', country_code)], context=context)
                if country_ids:
                    checkout['country_id'] = country_ids[0]

        internal_categs = self.internal_categories()

        values = {
            'countries': countries,
            'states': states,
            'int_categories': internal_categs,
            'checkout': checkout,
            'shipping_id': partner.id != shipping_id and shipping_id or 0,
            'shippings': shippings,
            'error': {},
            'has_check_vat': hasattr(registry['res.partner'], 'check_vat')
        }

        return values

    @http.route(['/shop/checkout'], type='http', auth="public", website=True)
    def checkout(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        order = request.website.sale_get_order(force_create=1, context=context)

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values()

        return request.website.render("website_sale.checkout", values)

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sale order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        cr, uid, context = request.cr, request.uid, request.context
        payment_obj = request.registry.get('payment.acquirer')
        sale_order_obj = request.registry.get('sale.order')

        order = request.website.sale_get_order(context=context)

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        shipping_partner_id = False
        if order:
            if order.partner_shipping_id.id:
                shipping_partner_id = order.partner_shipping_id.id
            else:
                shipping_partner_id = order.partner_invoice_id.id

        internal_categs = self.internal_categories()

        values = {
            'order': request.registry['sale.order'].browse(cr, SUPERUSER_ID, order.id, context=context),
            'int_categories':internal_categs
        }
        values['errors'] = sale_order_obj._get_errors(cr, uid, order, context=context)
        values.update(sale_order_obj._get_website_data(cr, uid, order, context))

        if not values['errors']:
            acquirer_ids = payment_obj.search(cr, SUPERUSER_ID, [('website_published', '=', True), ('company_id', '=', order.company_id.id)], context=context)
            values['acquirers'] = list(payment_obj.browse(cr, uid, acquirer_ids, context=context))
            render_ctx = dict(context, submit_class='btn btn-primary', submit_txt=_('Pay Now'))
            for acquirer in values['acquirers']:
                acquirer.button = payment_obj.render(
                    cr, SUPERUSER_ID, acquirer.id,
                    order.name,
                    order.amount_total,
                    order.pricelist_id.currency_id.id,
                    partner_id=shipping_partner_id,
                    tx_values={
                        'return_url': '/shop/payment/validate',
                    },
                    context=render_ctx)

        return request.website.render("website_sale.payment", values)

    @http.route(['/shop/confirmation'], type='http', auth="public", website=True)
    def payment_confirmation(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        cr, uid, context = request.cr, request.uid, request.context

        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
        else:
            return request.redirect('/shop')

        internal_categs = self.internal_categories()

        return request.website.render("website_sale.confirmation", {'order': order, 'int_categories':internal_categs})

    @http.route(['/page/website.contactus', '/page/contactus'], type='http', auth="public", website=True)
    def contact(self, **kwargs):
        internal_categs = self.internal_categories()
        values = {'int_categories':internal_categs}
        for field in ['description', 'partner_name', 'phone', 'contact_name', 'email_from', 'name']:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)
        values.update(kwargs=kwargs.items())

        return request.website.render("website.contactus", values)
        
class Binary(http.Controller):

    @http.route(['/website/logo.png'], type='http', auth="none", cors="*")
    def company_logo_website(self, dbname=None, **kw):
        imgname = 'logo_website.png'
        placeholder = functools.partial(get_module_resource, 'web', 'static', 'src', 'img')
        uid = None
        if request.session.db:
            dbname = request.session.db
            uid = request.session.uid
        elif dbname is None:
            dbname = db_monodb()

        if not uid:
            uid = openerp.SUPERUSER_ID

        if not dbname:
            response = http.send_file(placeholder(imgname))
        else:
            try:
                # create an empty
                registry = openerp.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    cr.execute("""SELECT c.logo_website, c.write_date
                                    FROM res_users u
                               LEFT JOIN res_company c
                                      ON c.id = u.company_id
                                   WHERE u.id = %s
                               """, (uid,))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_data = StringIO(str(row[0]).decode('base64'))
                        response = http.send_file(image_data, filename=imgname, mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception:
                response = http.send_file(placeholder(imgname))

        return response
