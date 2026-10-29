// Public UI automation contract. Change these names only with a documented migration.
export const COMMERCE_UI_VERSION = "1";
export const entityTestId = (scope, identity) =>
  `${scope}-${encodeURIComponent(String(identity))}`;
export const tableRow =
  (scope, identity = "id") =>
  (record) => ({
    "data-testid": entityTestId(`${scope}-row`, record[identity]),
    "data-record-id": String(record[identity]),
  });
