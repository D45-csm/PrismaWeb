from django.test import TestCase
from django.urls import reverse


class CarritoTests(TestCase):
    def test_resumen_no_cobra_envio_ni_ofrece_domicilio(self):
        response = self.client.get(reverse('carrito'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Envío')
        self.assertNotContains(response, 'Dirección de entrega')
