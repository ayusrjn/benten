import { Typography } from "antd";

export const Logo = ({
  collapsed,
  size = 34,
  rounded = true,
}: {
  collapsed?: boolean;
  size?: number;
  rounded?: boolean;
}) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: collapsed ? 0 : 12,
        fontWeight: 700,
        justifyContent: collapsed ? "center" : "flex-start",
        padding: collapsed ? "0" : "0 12px",
      }}
    >
      <img
        src="/icon.png"
        alt="Benten"
        width={size}
        height={size}
        style={{
          borderRadius: rounded ? "10px" : "0px",
        }}
      />

      {!collapsed && (
        <Typography.Text
          strong
          style={{
            fontSize: size > 34 ? 22 : 18,
            whiteSpace: "nowrap",
          }}
        >
          Benten
        </Typography.Text>
      )}
    </div>
  );
};
