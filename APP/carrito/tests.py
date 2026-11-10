from django.test import TestCase
from django.urls import reverse


class CarritoTests(TestCase):
    def test_resumen_no_cobra_envio_ni_ofrece_domicilio(self):
        response = self.client.get(reverse('carrito'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Carrito de compras')
        self.assertNotContains(response, 'Envío')
        self.assertNotContains(response, 'Dirección de entrega')

    def test_checkout_inicia_deshabilitado_y_muestra_opciones_en_modal(self):
        response = self.client.get(reverse('carrito'))

        self.assertContains(response, 'id="proceedToPayment" type="button" disabled')
        self.assertContains(response, 'Proceder al pago')
        self.assertContains(response, 'id="checkoutChoiceDialog"')
        self.assertContains(response, 'data-checkout-choice="mesa"')
        self.assertContains(response, 'Reservar una mesa')
        self.assertContains(response, 'data-checkout-choice="llevar"')
        self.assertContains(response, 'Para llevar')
        self.assertNotContains(response, 'id="checkoutSection"')
