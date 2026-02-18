describe('Test Setup', () => {
  test('Jest is working correctly', () => {
    expect(1 + 1).toBe(2);
  });

  test('MSW server is available', () => {
    expect(fetch).toBeDefined();
  });

  test('localStorage mock is available', () => {
    expect(localStorage.setItem).toBeDefined();
    expect(localStorage.getItem).toBeDefined();
  });
});
