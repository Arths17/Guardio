declare module "react-simple-maps" {
  import type { ComponentType, ReactNode, SVGProps } from "react";

  export interface ComposableMapProps {
    width?: number;
    height?: number;
    projection?: unknown;
    projectionConfig?: Record<string, unknown>;
    style?: React.CSSProperties;
    children?: ReactNode;
  }

  export interface ZoomableGroupProps {
    center?: [number, number];
    zoom?: number;
    children?: ReactNode;
  }

  export interface GeographiesProps {
    geography: string | object;
    children: (props: { geographies: GeoFeature[] }) => ReactNode;
  }

  export interface GeoFeature {
    rsmKey: string;
    [key: string]: unknown;
  }

  export interface GeographyProps extends SVGProps<SVGPathElement> {
    geography: GeoFeature;
    fill?: string;
    stroke?: string;
    strokeWidth?: number;
    style?: {
      default?: React.CSSProperties;
      hover?: React.CSSProperties;
      pressed?: React.CSSProperties;
    };
  }

  export const ComposableMap: ComponentType<ComposableMapProps>;
  export const ZoomableGroup: ComponentType<ZoomableGroupProps>;
  export const Geographies: ComponentType<GeographiesProps>;
  export const Geography: ComponentType<GeographyProps>;
}
