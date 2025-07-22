import datetime
from io import BytesIO
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from xhtml2pdf import pisa

from booking.models import Booking

DAYS = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
DAY_INDEX = {day: i for i, day in enumerate(DAYS)}

def generate_graph(bookings):
    daily_counts = {day: 0 for day in DAYS}
    for booking in bookings:
        day = booking.created_at.strftime('%A')
        if day in daily_counts:
            daily_counts[day] += 1

    plt.figure(figsize=(10, 5))
    plt.plot(DAYS, [daily_counts[day] for day in DAYS], marker='o', linestyle='-', color='blue')
    plt.title("\U0001F4CA Weekly Bookings")
    plt.xlabel("Day")
    plt.ylabel("Bookings")
    plt.grid(True)

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    return buffer

def generate_revenue_chart(bookings):
    daily_revenue = {day: 0.0 for day in DAYS}
    for booking in bookings:
        day = booking.created_at.strftime('%A')
        daily_revenue[day] += float(booking.actual_cost or 0)

    plt.figure(figsize=(10, 5))
    plt.plot(DAYS, [daily_revenue[day] for day in DAYS], marker='o', linestyle='-', color='purple')
    plt.title("💰 Actual Revenue by Day")
    plt.xlabel("Day")
    plt.ylabel("Revenue (EGP)")
    plt.grid(True)

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    return buffer

def generate_predictions(garage_id):
    bookings = Booking.objects.filter(garage_id=garage_id).order_by('created_at')
    if not bookings:
        return {day: 0 for day in DAYS}

    start_date = bookings[0].created_at.date()
    daily_counts = {}

    # Count bookings per date
    for booking in bookings:
        booking_date = booking.created_at.date()
        daily_counts[booking_date] = daily_counts.get(booking_date, 0) + 1

    sorted_dates = sorted(daily_counts.keys())
    features = []
    targets = []

    for i, current_date in enumerate(sorted_dates):
        day_index = current_date.weekday()
        is_weekend = 1 if day_index in [4, 5] else 0
        days_since_start = (current_date - start_date).days

        # Rolling average over past 7 days
        if i >= 7:
            past_week = sorted_dates[i-7:i]
            avg_last_week = np.mean([daily_counts[d] for d in past_week])
        else:
            avg_last_week = 0.0

        features.append([day_index, is_weekend, days_since_start, avg_last_week])
        targets.append(daily_counts[current_date])

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(features, targets)

    # Predict for next 7 days (starting today)
    future_predictions = {}
    today = datetime.date.today()
    for i in range(7):
        future_date = today + datetime.timedelta(days=i)
        day_index = future_date.weekday()
        is_weekend = 1 if day_index in [4, 5] else 0
        days_since_start = (future_date - start_date).days

        # Estimate avg past 7 days as last known value or 0
        recent_known = targets[-7:] if len(targets) >= 7 else targets
        avg_last_week = np.mean(recent_known) if recent_known else 0

        x = [[day_index, is_weekend, days_since_start, avg_last_week]]
        pred = model.predict(x)[0]
        future_predictions[DAYS[day_index]] = max(0, int(round(pred)))

    return future_predictions

def generate_prediction_chart(predictions):
    values = [predictions.get(day, 0) for day in DAYS]

    plt.figure(figsize=(10, 5))
    plt.plot(DAYS, values, marker='o', linestyle='-', color='green')
    plt.title("🔮 Predicted Bookings")
    plt.xlabel("Day")
    plt.ylabel("Predicted Bookings")
    plt.grid(True)

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    return buffer

def generate_predicted_revenue_chart(bookings):
    if not bookings:
        predicted_revenue = {day: 0 for day in DAYS}
    else:
        features = []
        targets = []
        start_date = bookings[0].created_at.date()

        for booking in bookings:
            if booking.actual_cost:
                day_index = DAY_INDEX[booking.created_at.strftime('%A')]
                is_weekend = 1 if booking.created_at.weekday() in [4, 5] else 0
                days_since_start = (booking.created_at.date() - start_date).days
                features.append([day_index, is_weekend, days_since_start])
                targets.append(float(booking.actual_cost))

        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(features, targets)

        predicted_revenue = {}
        for i, day in enumerate(DAYS):
            day_index = i
            is_weekend = 1 if day_index in [4, 5] else 0
            days_since_start = (datetime.date.today() - start_date).days + i
            x = [[day_index, is_weekend, days_since_start]]
            pred = model.predict(x)[0]
            predicted_revenue[day] = round(pred, 2)

    plt.figure(figsize=(10, 5))
    plt.plot(DAYS, [predicted_revenue[day] for day in DAYS], marker='o', linestyle='-', color='orange')
    plt.title("💡 Predicted Revenue")
    plt.xlabel("Day")
    plt.ylabel("Revenue (EGP)")
    plt.grid(True)

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    return buffer

def render_pdf(template_src, context_dict):
    html = render_to_string(template_src, context_dict)
    result = BytesIO()
    pisa.CreatePDF(BytesIO(html.encode("UTF-8")), dest=result)
    return result

def generate_and_send_report(garage_id, email):
    now = datetime.datetime.now()
    one_week_ago = now - datetime.timedelta(days=7)

    bookings = Booking.objects.select_related('driver', 'parking_spot', 'garage').filter(
        garage_id=garage_id,
        created_at__gte=one_week_ago
    )

    chart = generate_graph(bookings)
    predictions = generate_predictions(garage_id)
    prediction_chart = generate_prediction_chart(predictions)
    revenue_chart = generate_revenue_chart(bookings)
    predicted_revenue_chart = generate_predicted_revenue_chart(bookings)

    total_revenue = 0
    enriched_bookings = []

    for b in bookings:
        cost = float(b.actual_cost or 0)
        total_revenue += cost
        enriched_bookings.append({
            'user': b.driver.username if b.driver else 'Unknown',
            'created_at': b.created_at,
            'start_time': b.start_time,
            'end_time': b.end_time,
            'spot_number': b.parking_spot.slot_number if b.parking_spot else 'N/A',
            'actual_cost': f"{cost:.2f} EGP",
        })

    context = {
        'bookings': enriched_bookings,
        'generated_on': now.strftime('%Y-%m-%d'),
        'predictions': predictions,
        'total_revenue': f"{total_revenue:.2f} EGP",
        'garage_name': bookings[0].garage.name if bookings else "Unknown",
    }

    pdf = render_pdf('reports/weekly_report.html', context)

    email_msg = EmailMessage(
        subject='\U0001F4C4 Weekly Garage Report + \U0001F4CA Predictions',
        body='Attached is your weekly report with charts and prediction insights.',
        to=[email]
    )

    email_msg.attach('weekly_report.pdf', pdf.getvalue(), 'application/pdf')
    email_msg.attach('weekly_chart.png', chart.getvalue(), 'image/png')
    email_msg.attach('prediction_chart.png', prediction_chart.getvalue(), 'image/png')
    email_msg.attach('revenue_chart.png', revenue_chart.getvalue(), 'image/png')
    email_msg.attach('predicted_revenue_chart.png', predicted_revenue_chart.getvalue(), 'image/png')
    email_msg.send()