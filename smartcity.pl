% smartcity.pl
% Facts:
% area(NameAtom, Population, PollutionIndex, TrafficIndex, EnergyUsage, WasteLevel).
% All numeric indexes are integers 0..200 (example scale)

:- dynamic area/6.


% ---------- UNIVERSAL QUANTIFIER ----------
% true if all areas satisfy a given condition
forall_pollution_below(Threshold) :-
    \+ (area(_, _, Pollution, _, _, _), Pollution > Threshold). 

forall_traffic_below(Threshold) :-
    \+ (area(_, _, _, Traffic, _, _), Traffic > Threshold).

% ---------- EXISTENTIAL QUANTIFIER ----------
% true if at least one area satisfies a condition
exists_pollution_above(Threshold) :-
    area(_, _, Pollution, _, _, _), Pollution > Threshold.

exists_traffic_above(Threshold) :-
    area(_, _, _, Traffic, _, _, _), Traffic > Threshold.

% Sample data
area(city_center, 50000, 85, 90, 120, 60).
area(suburb_north, 15000, 45, 40, 60, 30).
area(industrial_zone, 12000, 110, 75, 150, 90).
area(downtown, 30000, 70, 65, 95, 55).
area(riverside, 8000, 30, 20, 40, 20).

% ---------
% Needs & services
% ---------
% If pollution > 70 -> needs waste/air management
needs_waste(Area) :- area(Area, _, Pollution, _, _, _), Pollution > 70.
needs_traffic(Area) :- area(Area, _, _, Traffic, _, _), Traffic > 70.
needs_energy(Area) :- area(Area, _, _, _, Energy, _), Energy > 100.
needs_waste_level(Area) :- area(Area, _, _, _, _, Waste), Waste > 70.

% Generic "can_service" predicate: service can be waste | traffic | energy | waste_level
can_service(Area, waste) :- needs_waste(Area).
can_service(Area, traffic) :- needs_traffic(Area).
can_service(Area, energy) :- needs_energy(Area).
can_service(Area, waste_level) :- needs_waste_level(Area).

% ---------
% Suggestion predicates (find all areas above threshold)
% --------- 
suggest_by_pollution(Threshold, L) :-
    findall(Name, (area(Name, _, Poll, _, _, _), Poll > Threshold), L).

suggest_by_traffic(Threshold, L) :-
    findall(Name, (area(Name, _, _, Traffic, _, _), Traffic > Threshold), L).

suggest_by_energy(Threshold, L) :-
    findall(Name, (area(Name, _, _, _, Energy, _), Energy > Threshold), L).


% ---------
% Recursion: sum population of a list of area atoms
% ---------
sum_population([], 0).
sum_population([H|T], Sum) :-
    area(H, Pop, _, _, _, _),
    sum_population(T, Rest),
    Sum is Pop + Rest.

% ---------
% Backtracking / findall examples
% ---------
areas_with_pollution_below(Threshold, L) :-
    findall(Name, (area(Name, _, Poll, _, _, _), Poll < Threshold), L).

% ---------
% Unification helper
% ---------
unify_city(Name, Pop, Poll, Traffic, Energy, Waste) :-
    area(Name, Pop, Poll, Traffic, Energy, Waste).

% allow assert of new area facts through Flask via assertz/1
% (Flask code does assertz(area(...)) directly)
