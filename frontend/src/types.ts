export type DecisionRow = {
  deliveryTime: string;
  decisionCutoff: string;
  selectedPublishTime: string | null;
  forecastMW: number | null;
  forecastHorizonHours: number | null;
  selectionStatus: string;
};

export type AccuracyRow = {
  deliveryTime: string;
  forecastMW: number;
  actualMW: number;
  errorMW: number;
  absoluteErrorMW: number;
  forecastHorizonHours?: number | null;
};

export type Summary = {
  metrics: {
    count: number;
    maeMW: number | null;
    rmseMW: number | null;
    biasMW: number | null;
    absoluteErrorP90MW: number | null;
  };
};
