# -*- coding: utf-8 -*-

from openerp import models
import logging

_logger = logging.getLogger(__name__)


class MRPProduction(models.Model):
    _inherit = 'mrp.production'

    def _get_bom_exploded(self, src_uom, qty, bom, properties=None):
        uom_obj = self.env['product.uom']
        bom_obj = self.env['mrp.bom']
        factor = uom_obj._compute_qty(src_uom, qty, bom.product_uom.id)
        return bom_obj._bom_explode(
            bom, self.product_id, factor / bom.product_qty,
            properties, routing_id=self.routing_id.id
        )

    def _get_ingredients_recursive(self, ilist, properties=None, ingredients=None):
        product_obj = self.env['product.product']
        bom_obj = self.env['mrp.bom']

        ingredients = ingredients or {}
        properties = properties or []
        for line in ilist:
            product = product_obj.browse(line['product_id'])
            bom = bom_obj.search([
                '|',
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('product_id', '=', product.id)
            ])

            if bom:
                # There should only be a single BOM
                if len(bom.ids) > 1:
                    if product in ingredients:
                        ingredients[product] += line['product_qty']
                    else:
                        ingredients[product] = line['product_qty']
                    _logger.debug("More than one Bill of Material found, so we do not care about it by now and count it as a needed ingredient!")
                else:
                    res = self._get_bom_exploded(
                        line['product_uom'],
                        line['product_qty'],
                        bom,
                        properties=properties
                    )
                    if res:
                        ingredients = self._get_ingredients_recursive(
                            res[0], ingredients=ingredients
                        )
                    else:
                        _logger.info("No ingredients found!")
            else:
                if product in ingredients:
                    ingredients[product] += line['product_qty']
                else:
                    ingredients[product] = line['product_qty']
        return ingredients

    def get_mrp_planned_list(self, product, product_qty, product_uom_id, purchase_list=None):
        bom_obj = self.env['mrp.bom']
        prod_obj = self.env['mrp.production']
        purchase_list = purchase_list or {}

        bom = bom_obj.search([
            '|',
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
            ('product_id', '=', product.id)
        ])
        if bom:
            # We assume that there should be only one BoM per product as we do not handle a choice of BoM during the calculation
            if len(bom.ids) > 1:
                if product in purchase_list:
                    purchase_list[product] += product_qty
                else:
                    purchase_list[product] = product_qty
                _logger.debug("More than one Bill of Material found, so we do not care about it by now and count it as a needed ingredient!")
            else:
                res = prod_obj._get_bom_exploded(
                    product_uom_id, product_qty, bom
                )
                if res:
                    purchase_list = prod_obj._get_ingredients_recursive(
                        res[0], ingredients=purchase_list
                    )
                else:
                    _logger.info("No ingredients found!")
        else:
            if product in purchase_list:
                purchase_list[product] += product_qty
            else:
                purchase_list[product] = product_qty

        return purchase_list
