// sherwood.html: the consent gate, the table parser, and the filters.
//
// Every test stubs the proxy fetch.  These are tests of the parser, not of
// sherweng.com being reachable, and a suite that reached out to a third-party
// CORS proxy would fail for reasons that have nothing to do with this page.

import { test, expect } from '@playwright/test';

const PAGE = '/sherwood.html';

// Two rows in the shape the real table uses: 13+ cells, the model in cell 0
// with an "Added" date, narrow dynamic range in cell 12.  The second row
// carries a footnote superscript, which the parser collects separately.
const TABLE_HTML = `
<html><body>
<p>Updated 4 February 2026</p>
<table>
  <tr>
    <td>Device Under Test</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td>
    <td>7</td><td>8</td><td>9</td><td>10</td><td>11</td><td>12</td><td>13</td>
  </tr>
  <tr>
    <td>Added 02/11/18 Elecraft K3</td><td>-140</td><td>2</td><td>3</td>
    <td>-138</td><td>5</td><td>6</td><td>7</td><td>Narrow</td><td>-115</td>
    <td>100</td><td>11</td><td>104</td>
  </tr>
  <tr>
    <td>Added 03/12/19 Icom IC-7300</td><td>-135</td><td>2</td><td>3</td>
    <td>-130</td><td>5</td><td>6</td><td>7</td><td>Wide</td><td>-110</td>
    <td>90</td><td>11</td><td>97<sup>a</sup></td>
  </tr>
</table>
</body></html>`;

/**
 * Answer every CORS proxy with the same canned table, so the first one wins
 * and the page never touches the network.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} [body] - HTML to serve as the fetched page
 */
async function stubProxies(page, body = TABLE_HTML) {
  await page.route('**/corsproxy.io/**', (route) =>
    route.fulfill({ status: 200, contentType: 'text/html', body }));
  // allorigins wraps the page in JSON; the other two return it raw.
  await page.route('**/api.allorigins.win/**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json',
                    body: JSON.stringify({ contents: body }) }));
  await page.route('**/thingproxy.freeboard.io/**', (route) =>
    route.fulfill({ status: 200, contentType: 'text/html', body }));
}

test('asks before fetching anything', async ({ page }) => {
  let fetched = false;
  await page.route('**/corsproxy.io/**', (route) => { fetched = true; route.abort(); });

  await page.goto(PAGE);
  await expect(page.locator('#permission-screen')).toBeVisible();
  await expect(page.locator('#dashboard')).toBeHidden();
  expect(fetched).toBe(false);
});

test('declining leaves the data unfetched', async ({ page }) => {
  let fetched = false;
  await page.route('**/corsproxy.io/**', (route) => { fetched = true; route.abort(); });

  await page.goto(PAGE);
  await page.getByRole('button', { name: 'No thanks' }).click();
  await expect(page.locator('#dashboard')).toBeHidden();
  expect(fetched).toBe(false);
});

test('parses the table into rows', async ({ page }) => {
  await stubProxies(page);
  await page.goto(PAGE);
  await page.getByRole('button', { name: 'Yes, fetch data' }).click();

  await expect(page.locator('#dashboard')).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(2);
  await expect(page.locator('tbody')).toContainText('Elecraft K3');
  await expect(page.locator('tbody')).toContainText('Icom IC-7300');
  // Cell 12 is narrow dynamic range.
  await expect(page.locator('tbody tr').first()).toContainText('104');
  await expect(page.locator('#data-date')).toContainText('4 February 2026');
});

test('search filters the rows', async ({ page }) => {
  await stubProxies(page);
  await page.goto(PAGE);
  await page.getByRole('button', { name: 'Yes, fetch data' }).click();
  await expect(page.locator('tbody tr')).toHaveCount(2);

  await page.locator('#search').fill('elecraft');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await expect(page.locator('tbody')).toContainText('Elecraft K3');
});

test('sorting by a column reorders the rows', async ({ page }) => {
  await stubProxies(page);
  await page.goto(PAGE);
  await page.getByRole('button', { name: 'Yes, fetch data' }).click();

  // Default sort is narrow DR descending, so the 104 dB radio leads.
  await expect(page.locator('tbody tr').first()).toContainText('Elecraft K3');
  await page.locator('th[data-col="drNarrow"]').click();
  await expect(page.locator('tbody tr').first()).toContainText('Icom IC-7300');
});

test('every proxy failing shows the error screen', async ({ page }) => {
  await page.route('**/corsproxy.io/**', (route) => route.abort());
  await page.route('**/api.allorigins.win/**', (route) => route.abort());
  await page.route('**/thingproxy.freeboard.io/**', (route) => route.abort());

  await page.goto(PAGE);
  await page.getByRole('button', { name: 'Yes, fetch data' }).click();

  await expect(page.locator('#error-screen')).toBeVisible();
  await expect(page.locator('#error-detail')).not.toBeEmpty();
});

test('falls through to the next proxy when the first fails', async ({ page }) => {
  await page.route('**/corsproxy.io/**', (route) => route.abort());
  await stubProxies(page);
  // stubProxies re-registers corsproxy; the abort above was registered first
  // and Playwright matches the most recently added route, so re-abort it.
  await page.route('**/corsproxy.io/**', (route) => route.abort());

  await page.goto(PAGE);
  await page.getByRole('button', { name: 'Yes, fetch data' }).click();

  await expect(page.locator('#dashboard')).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(2);
});
