# %% Paper & Ink: every colour at a glance
# The comments are the page, set in italic. The code sits underneath in soft
# colours: gold function calls, coral macros, blue keywords and types, teal
# strings, orange numbers and constants. Open this file in Zed to see the
# whole palette; run it to check that it is a real model.

using JuMP, HiGHS

# %% A bakery plans its week, as the students write it
"Deliver fresh bread to two cities from one bakery, at the lowest cost."
function bakery(capacity::Float64, verbose::Bool = false)
    cities = ["Hamburg", "Berlin"]
    cost = [2.5, 3.25]
    demand = [120, 80]

    model = Model(HiGHS.Optimizer)
    set_silent(model)
    @variable(model, 0 <= trucks[c = 1:2] <= 5, Int)
    @constraint(model, [c = 1:2], trucks[c] * 60 >= demand[c])
    @constraint(model, sum(trucks) <= capacity)
    @objective(model, Min, sum(cost[c] * trucks[c] for c in 1:2))

    verbose && println(model)
    optimize!(model)

    if termination_status(model) == OPTIMAL
        plan = value.(trucks)
        for (c, city) in enumerate(cities)
            println("$(rpad(city, 8)) -> $(plan[c]) trucks")
        end
        return plan
    else
        error("no feasible plan for capacity $capacity")
    end
end

plan = bakery(8.0, true)
@assert sum(plan) >= 3

# %% Where to find each colour
#   prose:        every `#` line and the docstring, in italic
#   calls:        Model, set_silent, optimize!, value, println, error (bold at definition)
#   macros:       @variable, @constraint, @objective, @assert
#   keywords:     function, for, in, if, else, return, end
#   types:        Float64, Bool, Int, HiGHS.Optimizer
#   strings:      "Hamburg", "no feasible plan for capacity $capacity"
#   numbers:      2.5, 3.25, 120, 60, 8.0
#   constants:    true, false, OPTIMAL
#   plain code:   model, cities, cost, demand, plan and the operators
#   punctuation:  brackets, commas, semicolons
