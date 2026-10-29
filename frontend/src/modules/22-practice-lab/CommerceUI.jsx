import React from "react";
import { Button, Input, Modal, Table } from "antd";
import { Search } from "lucide-react";
import { tableRow } from "./commerceLocator.js";

export function CommerceSearch({ label, ...props }) {
  return (
    <Input.Search
      {...props}
      aria-label={label}
      enterButton={
        <Button aria-label={`执行${label}`} icon={<Search size={16} />} />
      }
    />
  );
}

// Keep Ant Design's native table, focus handling, keyboard behavior and dialog portal.
// Business scopes add stable hooks without targeting Ant's generated DOM/classes.
export function CommerceTable({
  scope,
  label,
  identity = "id",
  onRow,
  ...props
}) {
  return (
    <section
      data-testid={`commerce-${scope}-table`}
      aria-label={label}
      className="commerce-table-region"
    >
      <Table
        {...props}
        rowKey={identity}
        onRow={(record, index) => ({
          ...onRow?.(record, index),
          ...tableRow(scope, identity)(record),
        })}
      />
    </section>
  );
}

export function CommerceModal({
  scope,
  confirmLoading,
  okButtonProps,
  cancelButtonProps,
  ...props
}) {
  return (
    <Modal
      {...props}
      destroyOnHidden
      confirmLoading={confirmLoading}
      okButtonProps={{
        ...okButtonProps,
        "data-testid": `commerce-${scope}-submit`,
      }}
      cancelButtonProps={{
        ...cancelButtonProps,
        disabled: confirmLoading || cancelButtonProps?.disabled,
        "data-testid": `commerce-${scope}-cancel`,
      }}
      modalRender={(node) =>
        React.cloneElement(node, {
          "data-testid": `commerce-${scope}-dialog`,
          "aria-busy": Boolean(confirmLoading),
        })
      }
    />
  );
}
