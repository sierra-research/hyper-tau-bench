"""Toolkit for the airline_plus domain: airline with a changed fee schedule."""

from tau2.domains.airline.tools import AirlineTools


class AirlinePlusTools(AirlineTools):
    """Airline tools with the airline+ fee schedule.

    The values here must match data/tau2/domains/airline_plus/delta_spec.yaml
    (asserted by the airline_plus tests).
    """

    INSURANCE_FEE_PER_PASSENGER = 45
    EXTRA_BAGGAGE_FEE = 65
    NEW_RESERVATION_IDS = ["MERMER", "MERMES", "MERMET"]
    NEW_PAYMENT_IDS = [8471205, 8471206, 8471207]
