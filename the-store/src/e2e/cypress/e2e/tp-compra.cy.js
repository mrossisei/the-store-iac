// Recibo propio: nunca usar una orden preexistente como evidencia de esta compra.
const tpSuite = Cypress.env('TP_RUN_ID') ? describe : describe.skip;
tpSuite('TP: compra correlacionable', () => {
  it('conserva carrito, compra y registra un ID nuevo', () => {
    const email = `tp-${Cypress.env('TP_RUN_ID')}@example.com`;
    cy.visit('/catalog/d27cf49f-b689-4a75-a249-d373e0330bb5');
    cy.get('#add-to-cart').click();
    cy.visit('/cart');
    cy.contains('The Quiet Quill').should('be.visible');
    cy.task('tpRestartCart');
    cy.reload();
    cy.contains('The Quiet Quill').should('be.visible');
    cy.visit('/checkout');
    for (const [id, value] of Object.entries({firstName: 'TP', lastName: 'Redes', email,
      streetAddress: '100 Main Street', city: 'Anytown', zipCode: '11111'})) {
      cy.get(`#${id}`).clear().type(value);
    }
    cy.get('#state').clear().type('CA');
    cy.get('#checkout-submit').click();
    cy.get('input[type="radio"]').first().check({force: true});
    cy.get('#checkout-submit').click();
    for (const [id, value] of Object.entries({cardHolder: 'TP Redes', cardNumber: '1234567890123456', expiryDate: '01/35', cvc: '123'})) {
      cy.get(`#${id}`).clear().type(value);
    }
    cy.get('#checkout-submit').click();
    cy.get('#order-total').should('contain.text', '$165');
    cy.contains('p', 'Order ID').next('p').invoke('text').then(text => {
      const order_id = text.trim();
      expect(order_id).to.match(/^[a-zA-Z0-9-]+$/);
      cy.task('tpReceipt', {order_id, email});
    });
  });
});
