from flask import Flask, render_template, request, redirect, url_for, jsonify
from pyswip import Prolog
import json

app = Flask(__name__)
prolog = Prolog()
prolog.consult("smartcity.pl")

@app.route("/")
def home():
    # Get all areas for dashboard
    areas_data = []
    try:
        q = "unify_city(Name, Pop, Poll, Traffic, Energy, Waste)"
        for sol in prolog.query(q):
            areas_data.append({
                "name": str(sol["Name"]),
                "population": sol["Pop"],
                "pollution": sol["Poll"],
                "traffic": sol["Traffic"],
                "energy": sol["Energy"],
                "waste": sol["Waste"]
            })
    except:
        pass
    
    return render_template("index.html", areas=areas_data)

# API endpoint for getting all areas data (for charts)
@app.route("/api/areas")
def get_areas():
    areas_data = []
    try:
        q = "unify_city(Name, Pop, Poll, Traffic, Energy, Waste)"
        for sol in prolog.query(q):
            areas_data.append({
                "name": str(sol["Name"]).replace('_', ' ').title(),
                "population": sol["Pop"],
                "pollution": sol["Poll"],
                "traffic": sol["Traffic"],
                "energy": sol["Energy"],
                "waste": sol["Waste"]
            })
    except:
        pass
    return jsonify(areas_data)

# Get detailed info about a specific area
@app.route("/api/area/<area_name>")
def get_area_detail(area_name):
    area = area_name.lower().replace(" ", "_")
    q = f"area({area}, Pop, Poll, Traffic, Energy, Waste)"
    res = list(prolog.query(q))
    
    if res:
        data = res[0]
        # Check which services are needed
        services = []
        if list(prolog.query(f"can_service({area}, waste)")):
            services.append("waste")
        if list(prolog.query(f"can_service({area}, traffic)")):
            services.append("traffic")
        if list(prolog.query(f"can_service({area}, energy)")):
            services.append("energy")
        
        return jsonify({
            "name": area_name,
            "population": data["Pop"],
            "pollution": data["Poll"],
            "traffic": data["Traffic"],
            "energy": data["Energy"],
            "waste": data["Waste"],
            "services_needed": services
        })
    return jsonify({"error": "Area not found"}), 404

# Check whether an area needs a particular service
@app.route("/check_service", methods=["POST"])
def check_service():
    area = request.form.get("area", "").lower()
    service = request.form.get("service", "").lower()

    q = f"can_service({area}, {service})"
    result = bool(list(prolog.query(q)))

    # Get area details for more context
    area_details = {}
    try:
        q_detail = f"area({area}, Pop, Poll, Traffic, Energy, Waste)"
        res = list(prolog.query(q_detail))
        if res:
            area_details = res[0]
    except:
        pass

    if result:
        message = f"{area.replace('_',' ').title()} needs the {service} service."
        status = "needed"
    else:
        message = f"{area.replace('_',' ').title()} does NOT (currently) need the {service} service."
        status = "not_needed"
    
    return render_template("result.html", 
                         message=message, 
                         destinations=[], 
                         status=status,
                         area_details=area_details,
                         service=service)

# Suggest areas that match a need threshold
@app.route("/suggest", methods=["POST"])
def suggest():
    need = request.form.get("need", "").lower()
    threshold = request.form.get("threshold", "")
    try:
        threshold = int(threshold)
    except:
        threshold = 0

    if need == "pollution":
        q = f"suggest_by_pollution({threshold}, L)"
    elif need == "traffic":
        q = f"suggest_by_traffic({threshold}, L)"
    elif need == "energy":
        q = f"suggest_by_energy({threshold}, L)"
    elif need == "waste":
        q = f"suggest_by_waste({threshold}, L)"
    else:
        return render_template("result.html", message="Unknown need type.", destinations=[])

    res = list(prolog.query(q))
    if res and res[0].get("L") is not None:
        raw = res[0]["L"]
        areas = [str(a) for a in raw]
    else:
        areas = []

    # Get detailed info for matching areas
    areas_details = []
    for area in areas:
        try:
            q_detail = f"area({area}, Pop, Poll, Traffic, Energy, Waste)"
            detail_res = list(prolog.query(q_detail))
            if detail_res:
                areas_details.append({
                    "name": area.replace('_', ' ').title(),
                    "population": detail_res[0]["Pop"],
                    "pollution": detail_res[0]["Poll"],
                    "traffic": detail_res[0]["Traffic"],
                    "energy": detail_res[0]["Energy"],
                    "waste": detail_res[0]["Waste"]
                })
        except:
            pass

    if areas:
        message = f"Found {len(areas)} area(s) with {need} level above {threshold}"
    else:
        message = f"No areas match {need} > {threshold}."
    
    return render_template("result.html", 
                         message=message, 
                         destinations=areas_details,
                         need_type=need,
                         threshold=threshold)

# Add an area fact
@app.route("/add_fact", methods=["GET", "POST"])
def add_fact():
    if request.method == "POST":
        name = request.form.get("name", "").lower().strip().replace(" ", "_")
        population = int(request.form.get("population", 0))
        pollution = int(request.form.get("pollution", 0))
        traffic = int(request.form.get("traffic", 0))
        energy = int(request.form.get("energy", 0))
        waste = int(request.form.get("waste", 0))

        fact = f"assertz(area({name}, {population}, {pollution}, {traffic}, {energy}, {waste}))"
        list(prolog.query(fact))
        return redirect(url_for("home"))

    return render_template("add_fact.html")

# Recursion example: sum populations of a list of areas
@app.route("/recursion", methods=["POST"])
def recursion_sum():
    raw = request.form.get("areas", "")
    names = [n.strip().lower().replace(" ", "_") for n in raw.split(",") if n.strip()]
    if not names:
        return render_template("result.html", message="Provide at least one area (comma separated).", destinations=[])

    prolog_list = "[" + ",".join(names) + "]"
    q = f"sum_population({prolog_list}, Sum)"
    res = list(prolog.query(q))
    if res:
        total = res[0]["Sum"]
        message = f"Total population for {', '.join([n.replace('_',' ').title() for n in names])} is {total:,}."
        
        # Get individual areas for breakdown
        areas_breakdown = []
        for name in names:
            q_detail = f"area({name}, Pop, Poll, Traffic, Energy, Waste)"
            detail_res = list(prolog.query(q_detail))
            if detail_res:
                areas_breakdown.append({
                    "name": name.replace('_', ' ').title(),
                    "population": detail_res[0]["Pop"]
                })
    else:
        message = "Could not compute total — make sure all areas exist in knowledge base."
        areas_breakdown = []
        total = 0
    
    return render_template("result.html", 
                         message=message, 
                         destinations=areas_breakdown,
                         total_population=total)

# Backtracking example: find all areas with pollution below a threshold
@app.route("/backtrack", methods=["POST"])
def backtrack():
    threshold = int(request.form.get("pollution_threshold", 0))
    q = f"areas_with_pollution_below({threshold}, L)"
    res = list(prolog.query(q))
    if res and res[0].get("L") is not None:
        matches = [str(d) for d in res[0]["L"]]
    else:
        matches = []

    # Get detailed info for clean areas
    clean_areas = []
    for area in matches:
        try:
            q_detail = f"area({area}, Pop, Poll, Traffic, Energy, Waste)"
            detail_res = list(prolog.query(q_detail))
            if detail_res:
                clean_areas.append({
                    "name": area.replace('_', ' ').title(),
                    "population": detail_res[0]["Pop"],
                    "pollution": detail_res[0]["Poll"],
                    "traffic": detail_res[0]["Traffic"],
                    "energy": detail_res[0]["Energy"],
                    "waste": detail_res[0]["Waste"]
                })
        except:
            pass

    if matches:
        message = f"Found {len(matches)} clean area(s) with pollution below {threshold}"
    else:
        message = f"No areas with pollution below {threshold}."
    
    return render_template("result.html", 
                         message=message, 
                         destinations=clean_areas,
                         is_clean_search=True,
                         threshold=threshold)

# Unification example: query a city's full tuple
@app.route("/unify", methods=["POST"])
def unify():
    area = request.form.get("area_u", "").lower().strip().replace(" ", "_")
    q = "unify_city(Name, Pop, Poll, Traffic, Energy, Waste)"
    conditions = []
    if area:
        conditions.append(f"Name = {area}")
        q = "unify_city(Name, Pop, Poll, Traffic, Energy, Waste)," + ", ".join(conditions)

    results = []
    for sol in prolog.query(q):
        # Check services for each area
        area_name = str(sol["Name"])
        services = []
        if list(prolog.query(f"can_service({area_name}, waste)")):
            services.append("waste")
        if list(prolog.query(f"can_service({area_name}, traffic)")):
            services.append("traffic")
        if list(prolog.query(f"can_service({area_name}, energy)")):
            services.append("energy")
        
        results.append({
            "area": area_name.replace('_', ' ').title(),
            "population": sol["Pop"],
            "pollution": sol["Poll"],
            "traffic": sol["Traffic"],
            "energy": sol["Energy"],
            "waste": sol["Waste"],
            "services": services
        })

    if results:
        message = f"Found {len(results)} area(s) matching your query"
    else:
        message = "No results found."
    
    return render_template("result.html", 
                         message=message, 
                         destinations=results,
                         is_unify=True)

# Compare multiple areas
@app.route("/compare", methods=["GET", "POST"])
def compare():
    if request.method == "POST":
        raw = request.form.get("compare_areas", "")
        names = [n.strip().lower().replace(" ", "_") for n in raw.split(",") if n.strip()]
        
        if len(names) < 2:
            return render_template("compare.html", 
                                 error="Please provide at least 2 areas to compare")
        
        areas_data = []
        for area in names:
            q = f"area({area}, Pop, Poll, Traffic, Energy, Waste)"
            res = list(prolog.query(q))
            if res:
                services = []
                if list(prolog.query(f"can_service({area}, waste)")):
                    services.append("waste")
                if list(prolog.query(f"can_service({area}, traffic)")):
                    services.append("traffic")
                if list(prolog.query(f"can_service({area}, energy)")):
                    services.append("energy")
                
                areas_data.append({
                    "name": area.replace('_', ' ').title(),
                    "population": res[0]["Pop"],
                    "pollution": res[0]["Poll"],
                    "traffic": res[0]["Traffic"],
                    "energy": res[0]["Energy"],
                    "waste": res[0]["Waste"],
                    "services": services
                })
        
        return render_template("compare.html", areas_data=areas_data)
    
    return render_template("compare.html")

# Analytics dashboard
@app.route("/analytics")
def analytics():
    return render_template("analytics.html")

@app.route("/quantifiers", methods=["POST"])
def quantifiers():
    q_type = request.form.get("quantifier")
    category = request.form.get("category")
    threshold = int(request.form.get("threshold", 0))

    if q_type == "universal":
        if category == "pollution":
            query = f"forall_pollution_below({threshold})"
            statement = f"All areas have pollution below {threshold}."
        elif category == "traffic":
            query = f"forall_traffic_below({threshold})"
            statement = f"All areas have traffic below {threshold}."
    elif q_type == "existential":
        if category == "pollution":
            query = f"exists_pollution_above({threshold})"
            statement = f"There exists at least one area with pollution above {threshold}."
        elif category == "traffic":
            query = f"exists_traffic_above({threshold})"
            statement = f"There exists at least one area with traffic above {threshold}."
    else:
        return render_template("result.html", message="Invalid quantifier type.", destinations=[])

    result = bool(list(prolog.query(query)))
    message = f"✅ {statement}" if result else f"❌ Not true: {statement}"

    return render_template("result.html", message=message, destinations=[])


if __name__ == "__main__":
    app.run(debug=True)