declare module 'react-force-graph-2d' {
  import { Component } from 'react';

  export interface ForceGraphProps {
    graphData: {
      nodes: any[];
      links: any[];
    };
    nodeLabel?: string | ((node: any) => string);
    nodeAutoColorBy?: string | ((node: any) => string);
    nodeRelSize?: number;
    linkColor?: string | ((link: any) => string);
    width?: number;
    height?: number;
    nodeCanvasObject?: (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => void;
  }

  export class ForceGraph2D extends Component<ForceGraphProps> {}
}