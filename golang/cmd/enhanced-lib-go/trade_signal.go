package main

import (
	"fmt"
	"math"
)

func getRange(_range [2]float64, divisor int, places string) []float64 {
	difference := _range[1] - _range[0]
	var factor float64

	if divisor == 0 {
		factor = 0
	} else {
		factor = difference / float64(divisor)
	}

	var result []float64
	for i := 0; i < divisor; i++ {
		result = append(result, _range[0]+float64(i)*factor)
	}
	result = append(result, _range[1])

	return result
}

func getTradeZone(currentPrice float64, array [2]float64, risk int, places string) (float64, float64) {
	zones := getRange(array, risk, places)
	var considered []int

	for i, x := range zones {
		if x > currentPrice {
			considered = append(considered, i)
		}
	}

	if len(considered) > 0 && considered[0] > 0 {
		return zones[considered[0]-1], zones[considered[0]]
	}

	return 0, 0 // Change the return type to match the actual types used in your application
}

type Signal struct {
	Focus              float64
	Budget             float64
	PercentChange      float64
	PricePlaces        string
	DecimalPlaces      string
	ZoneRisk           float64
	Fee                float64
	Support            *float64
	RiskReward         float64
	Resistance         *float64
	TakeProfit         *float64
	RiskPerTrade       *float64
	IncreaseSize       *bool
	AdditionalIncrease float64
	MinimumPnl         *float64
	Split              *int
	MaxSize            *float64
	TradeSize          *float64
	IncreasePosition   *bool
	Default            *bool
	MinimumSize        *float64
}

func (s *Signal) Risk() float64 {
	return s.Budget * s.PercentChange
}

func (s *Signal) MinTrades() int {
	return int(s.Risk())
}

func (s *Signal) MinPrice() float64 {
	number := s.PricePlaces
	number = number[2 : len(number)-1] // removing "%." and "f"
	exp := -int(number)
	return 1 * math.Pow10(exp)
}

func (s *Signal) GetRange(currentPrice float64, kind string) []float64 {
	var zones []float64
	risk := int(s.Risk())
	futureRange := s.getFutureRange(currentPrice)

	if len(futureRange) > 0 {
		zones = getRange(futureRange, risk, s.PricePlaces)
		if kind == "short" {
			secondFutureRange := s.getFutureRange(futureRange[0] - s.MinPrice())
			if len(secondFutureRange) > 0 {
				secondaryZones := getRange(secondFutureRange, risk, s.PricePlaces)
				zones = append(zones, secondaryZones...)

				thirdFutureRange := s.getFutureRange(futureRange[1] + s.MinPrice())
				if len(thirdFutureRange) > 0 {
					thirdZones := getRange(thirdFutureRange, risk, s.PricePlaces)
					zones = append(zones, thirdZones...)
					sort.Float64s(zones)
				}
			}
		}
	}

	return zones
}

func (s *Signal) toF(number float64) float64 {
	return float64(fmt.Sprintf(s.PricePlaces, number))
}


func (s *Signal) getFutureRange(currentPrice float64) (float64, float64) {
	marginRange := s.getMarginRange(currentPrice)
	if len(marginRange) > 0 {
		futureZone := getTradeZone(currentPrice, marginRange, int(s.Risk()), s.PricePlaces)
		if futureZone[0] != 0 && futureZone[1] != 0 {
			return s.toF(futureZone[0]), s.toF(futureZone[1])
		}
	}
	return 0, 0 // Change the return type to match the actual types used in your application
}


func NewSignal(focus, budget float64) *Signal {
	return &Signal{
		Focus:              focus,
		Budget:             budget,
		PercentChange:      0.02,
		PricePlaces:        "%.5f",
		DecimalPlaces:      "%.0f",
		ZoneRisk:           1,
		Fee:                0.08 / 100,
		RiskReward:         4,
		AdditionalIncrease: 0,
	}
}
