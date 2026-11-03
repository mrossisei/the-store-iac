import { Checkout } from '../models/Checkout';
import { HttpOrdersService } from './HttpOrdersService';

describe('HttpOrdersService contract with Orders', () => {
  const checkout = {
    shippingAddress: {
      firstName: 'TP', lastName: 'Redes', email: 'probe@example.com',
      address1: '100 Main Street', city: 'Anytown', state: 'CA', zip: '11111',
    },
    items: [{ id: 'product', name: 'Probe', quantity: 2, price: 100, totalCost: 200 }],
  } as Checkout;

  afterEach(() => jest.restoreAllMocks());

  it('sends nested address and correct product, unit cost and total cost', async () => {
    const request = jest.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ id: 'new-order' }), { status: 200 }));
    expect(await new HttpOrdersService('http://orders').create(checkout)).toEqual({ id: 'new-order' });
    expect(request.mock.calls[0][0]).toBe('http://orders/orders');
    expect(JSON.parse(request.mock.calls[0][1]!.body as string)).toEqual({
      shippingAddress: {
        firstName: 'TP', lastName: 'Redes', email: 'probe@example.com',
        address1: '100 Main Street', city: 'Anytown', state: 'CA', zipCode: '11111',
      },
      items: [{ productId: 'product', quantity: 2, unitCost: 100, totalCost: 200 }],
    });
  });

  it('rejects failed Orders requests without returning an apparent purchase', async () => {
    jest.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('private backend diagnostic', { status: 500 }));
    await expect(new HttpOrdersService('http://orders').create(checkout)).rejects.toThrow('Orders HTTP 500');
  });
});
