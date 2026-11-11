from django.test import TestCase
from django.urls import reverse


class CarritoTests(TestCase):
    def test_resumen_no_cobra_envio_ni_ofrece_domicilio(self):
        response = self.client.get(reverse('carrito'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Carrito de compras')
        self.assertNotContains(response, 'Envío')
        self.assertNotContains(response, 'Dirección de entrega')

    def test_checkout_inicia_deshabilitado_y_no_muestra_modal_de_opciones(self):
        response = self.client.get(reverse('carrito'))

        self.assertContains(response, 'id="proceedToPayment" type="button" disabled')
        self.assertContains(response, 'Proceder al pago')
        self.assertNotContains(response, 'checkoutChoiceDialog')
        self.assertNotContains(response, 'data-checkout-choice')
        self.assertNotContains(response, 'id="checkoutSection"')

    def test_resumen_muestra_control_para_vaciar_carrito(self):
        response = self.client.get(reverse('carrito'))

        self.assertContains(response, 'id="clearCartButton"')
        self.assertContains(response, 'onclick="vaciarCarrito()"')
        self.assertContains(response, 'aria-label="Vaciar carrito"')
        self.assertNotContains(response, 'aria-label="Notificaciones"')
        self.assertContains(response, 'logo_prisma_header.png')
