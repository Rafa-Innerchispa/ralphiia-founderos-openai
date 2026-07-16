# Supplier sourcing determinista

`quoteops.supplier_sourcing` conserva cada oferta por SKU canónico; una nueva lista se agrega como otra `SupplierOffer`, sin sustituir las ofertas de ZC Mayoristas. El módulo no hace I/O, no usa modelos y nunca compra automáticamente.

## Contrato operativo

Una oferta lleva `canonical_item_id`, identidad/referencia de proveedor, costo unitario, cantidad, moneda, impuesto conocido/desconocido, flete y otros costos, disponibilidad/stock, lead time, vigencia, fuente/evidencia, modo de pago, días y estado de crédito. Los importes son `Decimal`. Un valor desconocido queda como `None`: no se estima impuesto, flete, stock ni crédito.

Sólo USD es moneda soportada inicialmente. Una oferta con costo, cantidad, impuesto, flete u otros costos desconocidos; sin disponibilidad confirmada; vencida; insuficiente; no disponible; o con moneda no soportada queda marcada como no elegible y conserva sus razones. El costo puesto total es `unit_cost * quantity + tax_amount + shipping_cost + other_cost`.

`recommend_offer()` siempre expone `lowest_cost_offer`, `best_confirmed_credit_offer`, delta absoluto/porcentual, elegibilidad y razones. Por defecto —política configurable `max_credit_premium_pct=5`— recomienda una oferta con `current_confirmed` si su costo puesto no supera en 5% a la más barata válida. Si lo supera, recomienda la más barata y mantiene la alternativa de crédito visible. `historical_observed` nunca activa preferencia y añade aviso de reconfirmación; los otros estados son `unverified` y `unavailable`.

## Identidad y conciliación

`reconcile_supplier_records()` cruza primero `tax_id`/RUC, luego `party_id`. Los nombres normalizados generan únicamente candidatos: si son ambiguos no fusiona entidades. Cada registro conserva su origen: `contifico`, `crm`, `legacy` o `invoice_history`.

## Evidencia disponible (no equivale a crédito actual)

- QuoteOps staging: 39 líneas en 2 ofertas, únicamente ZC Mayoristas.
- RalphiIA: 646 proveedores Contífico; 647 CRM parties con rol supplier; 17 legacy suppliers; 33 `inventory_offers`; ningún item tiene hoy más de una oferta global.
- XML histórico: 2.064 facturas, 127 emisores crudos. ZC Mayoristas aparece en 384; existen 160 registros de plazo 30 días y 19 de 45 días.

Los plazos XML son evidencia histórica (`historical_observed`), no crédito vigente (`current_confirmed`).
