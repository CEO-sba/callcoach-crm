"""
CallCoach CRM - Pre-built Nurture Sequence Templates
40+ procedure-specific 6-month follow-up sequences with persuasive, converting messages.
Each sequence has 10-12 steps spread over 180 days.
Placeholders: {name}, {procedure}, {clinic_name}, {doctor_name}, {booking_link}, {phone}
"""

NURTURE_TEMPLATES = {

    # =========================================================================
    # HAIR PROCEDURES
    # =========================================================================

    "hair_transplant_fue": {
        "name": "Hair Transplant (FUE) - 6 Month Nurture",
        "description": "Complete nurture sequence for FUE hair transplant leads",
        "procedure_category": "hair_transplant_fue",
        "steps": [
            {
                "step_number": 1, "delay_hours": 0, "delay_type": "hours",
                "message_template": "Hi {name}, thank you for your interest in hair transplant at {clinic_name}. I'm reaching out from {doctor_name}'s team. We understand that hair loss can be a deeply personal concern, and we're here to help you explore the best solution. Would you like to know more about our FUE procedure or schedule a consultation?",
            },
            {
                "step_number": 2, "delay_hours": 24, "delay_type": "days",
                "message_template": "Hi {name}, just wanted to share some quick info about FUE hair transplant. It's a minimally invasive procedure where individual hair follicles are extracted and transplanted to thinning areas. No linear scar, natural-looking results, and most patients return to work within a week. {doctor_name} has performed hundreds of successful procedures. Would you like to see some before-after results?",
            },
            {
                "step_number": 3, "delay_hours": 72, "delay_type": "days",
                "message_template": "Hi {name}, many of our patients had the same questions before their hair transplant. Here are the top 3 things they wished they knew earlier:\n\n1. The sooner you address hair loss, the better the results\n2. FUE is virtually painless with local anesthesia\n3. Results start showing in 3-4 months, full results by 12 months\n\nWant to book a free assessment with {doctor_name}? {booking_link}",
            },
            {
                "step_number": 4, "delay_hours": 168, "delay_type": "days",
                "message_template": "Hi {name}, hope you're doing well. Just wanted to let you know that {doctor_name} recently shared some incredible transformation results from our hair transplant patients. The confidence boost these patients experience is truly life-changing. If you're still considering the procedure, we'd love to answer any questions. Feel free to reply here or call us at {phone}.",
            },
            {
                "step_number": 5, "delay_hours": 336, "delay_type": "days",
                "message_template": "Hi {name}, quick check-in from {clinic_name}. We noticed you were interested in hair transplant. Many of our patients tell us they wish they hadn't waited so long to take the step. The thing about hair loss is that it's progressive, so the earlier you act, the more options you have. Would you like to schedule a no-obligation consultation this week? {booking_link}",
            },
            {
                "step_number": 6, "delay_hours": 720, "delay_type": "days",
                "message_template": "Hi {name}, it's been a month since you first reached out to {clinic_name}. We wanted to share that {doctor_name} uses the latest Direct FUE technique which means faster recovery, higher graft survival, and more natural density. If cost was a concern, we also offer flexible payment plans. Would you like to discuss your options? {booking_link}",
            },
            {
                "step_number": 7, "delay_hours": 1440, "delay_type": "days",
                "message_template": "Hi {name}, just a friendly update from {clinic_name}. We've recently upgraded our facilities and techniques for even better hair transplant results. {doctor_name} continues to achieve outstanding outcomes for our patients. If you've been thinking about it, this could be a great time to book your consultation. Reply 'yes' and we'll set it up for you.",
            },
            {
                "step_number": 8, "delay_hours": 2160, "delay_type": "days",
                "message_template": "Hi {name}, we know making a decision about hair transplant takes time, and that's completely okay. We just want you to know that our team at {clinic_name} is here whenever you're ready. {doctor_name} offers personalized treatment plans because every case is unique. No pressure at all. Whenever you're ready, we're here. {booking_link}",
            },
            {
                "step_number": 9, "delay_hours": 2880, "delay_type": "days",
                "message_template": "Hi {name}, hope you're doing great. This is a gentle reminder from {clinic_name}. Many of our happiest patients initially took months to decide, and they all say the same thing: 'I wish I'd done it sooner.' If you'd like to revisit your options or just have a quick chat with {doctor_name}'s team, we're just a message away. {phone}",
            },
            {
                "step_number": 10, "delay_hours": 3600, "delay_type": "days",
                "message_template": "Hi {name}, it's been a while since we connected. At {clinic_name}, we believe in giving patients all the time they need. Just wanted to let you know our doors are always open if you'd like to explore hair restoration options. {doctor_name}'s team would be happy to do a fresh assessment anytime. Wishing you all the best! {booking_link}",
            },
        ]
    },

    "hair_transplant_fut": {
        "name": "Hair Transplant (FUT) - 6 Month Nurture",
        "description": "Nurture sequence for FUT strip method hair transplant leads",
        "procedure_category": "hair_transplant_fut",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for your interest in hair restoration at {clinic_name}. {doctor_name}'s team specializes in the FUT technique which allows us to transplant a higher number of grafts in a single session. Would you like to learn more about how it works?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, FUT (Follicular Unit Transplantation) is ideal for patients who need maximum coverage. It allows {doctor_name} to harvest a strip of donor hair, which means more grafts per session compared to FUE. The linear scar is easily hidden by surrounding hair. Want to know if FUT is the right option for you?"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, here's what makes FUT at {clinic_name} different:\n\n1. Higher graft count per session (up to 4000+ grafts)\n2. {doctor_name}'s precise technique minimizes scarring\n3. Ideal for advanced hair loss stages\n4. Cost-effective compared to multiple FUE sessions\n\nBook a free assessment: {booking_link}"},
            {"step_number": 4, "delay_hours": 168, "delay_type": "days", "message_template": "Hi {name}, one of the most common concerns about FUT is the scar. At {clinic_name}, {doctor_name} uses a trichophytic closure technique that makes the scar virtually invisible once healed. Most of our patients wear short hairstyles with confidence. Would you like to see results? {phone}"},
            {"step_number": 5, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, just checking in. If you're comparing FUE vs FUT, {doctor_name} can help you understand which is better for your specific case during a consultation. Every patient is unique, and the best approach depends on your hair loss pattern and goals. Book your slot: {booking_link}"},
            {"step_number": 6, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, it's been a month since you first inquired. We wanted to remind you that {clinic_name} offers flexible payment options for hair transplant procedures. {doctor_name} believes everyone deserves to feel confident. Let us know if you'd like to explore this further."},
            {"step_number": 7, "delay_hours": 1440, "delay_type": "days", "message_template": "Hi {name}, quick update from {clinic_name}. We've been getting amazing results with our hair transplant patients lately. The transformations are truly remarkable. If you've been on the fence, now might be a great time to take the next step. Reply here or call {phone}."},
            {"step_number": 8, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, we understand that hair transplant is a big decision. Take all the time you need. We just want you to know that {doctor_name} and the team at {clinic_name} are here to answer any questions, no matter how small. We're rooting for you! {booking_link}"},
            {"step_number": 9, "delay_hours": 3600, "delay_type": "days", "message_template": "Hi {name}, final check-in from {clinic_name}. Whether you decide to proceed now or in the future, we're always here to help. Hair restoration technology keeps improving, and {doctor_name} stays at the forefront. Whenever you're ready, reach out. Wishing you the best! {phone}"},
        ]
    },

    "prp_hair": {
        "name": "PRP Hair Therapy - 6 Month Nurture",
        "description": "Nurture sequence for PRP hair loss treatment leads",
        "procedure_category": "prp_hair",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for your interest in PRP hair therapy at {clinic_name}. PRP (Platelet-Rich Plasma) is a non-surgical treatment that uses your own blood's growth factors to stimulate hair growth. Would you like to know if PRP is right for your hair concern?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, here's why PRP is becoming one of the most popular hair treatments:\n\n- Non-surgical, no downtime\n- Uses your body's natural healing factors\n- Sessions take only 30-45 minutes\n- Visible improvement in 3-6 months\n- Can be combined with other treatments for enhanced results\n\nWant to book a consultation with {doctor_name}? {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, a common question we get: 'How many PRP sessions do I need?' Most patients see best results with 3-4 sessions spaced 4 weeks apart, followed by maintenance sessions every 3-6 months. {doctor_name} will create a personalized plan based on your hair condition. Interested? {booking_link}"},
            {"step_number": 4, "delay_hours": 168, "delay_type": "days", "message_template": "Hi {name}, PRP works best when started early in hair thinning. The sooner you begin treatment, the better the outcomes. At {clinic_name}, we use advanced centrifuge technology to maximize platelet concentration. Would you like to schedule your first session? {phone}"},
            {"step_number": 5, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, just checking in from {clinic_name}. If you're exploring options for hair loss, PRP can be an excellent standalone treatment or a complement to hair transplant. {doctor_name} can assess which approach suits you best. Book your consultation: {booking_link}"},
            {"step_number": 6, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, wanted to let you know that {clinic_name} offers PRP packages that make the treatment more affordable. Starting your PRP journey sooner means better results. Would you like details on our treatment packages? Reply here or call {phone}."},
            {"step_number": 7, "delay_hours": 1440, "delay_type": "days", "message_template": "Hi {name}, many of our PRP patients report noticeable reduction in hair fall within the first month, with visible thickening by month 3. The results are gradual but impressive. If you'd like to start your journey, {doctor_name}'s team is ready. {booking_link}"},
            {"step_number": 8, "delay_hours": 2880, "delay_type": "days", "message_template": "Hi {name}, hope you're doing well. This is a friendly reminder that {clinic_name} is here whenever you're ready to address your hair concerns. PRP and other treatments continue to advance, and {doctor_name} stays updated with the latest techniques. Reach out anytime! {phone}"},
        ]
    },

    "scalp_micropigmentation": {
        "name": "Scalp Micropigmentation - 6 Month Nurture",
        "description": "Nurture sequence for SMP leads",
        "procedure_category": "scalp_micropigmentation",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thanks for your interest in Scalp Micropigmentation (SMP) at {clinic_name}. SMP creates the appearance of a fuller head of hair by depositing micro-pigments into the scalp. It's perfect for adding density, camouflaging scars, or creating a buzz-cut look. Would you like to learn more?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, SMP at {clinic_name} offers:\n\n- Immediate visible results\n- Non-surgical, minimal discomfort\n- Natural-looking hairline design\n- Works for all stages of hair loss\n- Results last 3-5 years\n\n{doctor_name} designs each hairline to match your face shape and age. Book a free consultation: {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, most SMP treatments require 2-3 sessions spaced a week apart. The whole process is completed within a month, and you'll see results from day one. Our patients love the natural, low-maintenance look. Want to see before-after photos? Reply 'yes' or call {phone}."},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, still considering SMP? Here's what our patients say: it's the best decision they made for their confidence. No daily maintenance, no side effects, and an instant transformation. {doctor_name} at {clinic_name} ensures every result looks 100% natural. Ready to take the step? {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in from {clinic_name}. If you've been researching SMP, we're happy to answer any remaining questions. Whether it's about the procedure, aftercare, or pricing, our team is here to help. Reply here or call {phone}."},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, just a friendly note from {clinic_name}. SMP continues to grow in popularity as men and women discover this life-changing treatment. If you're ready to explore your options, {doctor_name}'s team would love to help. Book anytime: {booking_link}"},
            {"step_number": 7, "delay_hours": 3600, "delay_type": "days", "message_template": "Hi {name}, final check-in from {clinic_name}. We're here whenever you decide to take the next step. Wishing you all the best, and remember, great confidence starts with how you feel about yourself. {phone}"},
        ]
    },

    # =========================================================================
    # PLASTIC SURGERY
    # =========================================================================

    "rhinoplasty": {
        "name": "Rhinoplasty - 6 Month Nurture",
        "description": "Nurture sequence for nose surgery leads",
        "procedure_category": "rhinoplasty",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for reaching out to {clinic_name} about rhinoplasty. We understand this is a significant decision, and {doctor_name} is here to help you achieve a result that enhances your natural features. Would you like to schedule a consultation to discuss your goals?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, rhinoplasty at {clinic_name} is customized for each patient. {doctor_name} uses advanced 3D imaging during consultation so you can actually visualize the expected outcome before surgery. This helps set realistic expectations and ensures we're aligned on your goals. Interested in seeing what's possible? {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, common questions about rhinoplasty:\n\n1. Recovery: Most patients return to work in 7-10 days\n2. Pain: Manageable with prescribed medication\n3. Results: Final shape settles in 6-12 months\n4. Breathing: Can be improved if there are structural issues\n\n{doctor_name} addresses both aesthetic and functional concerns. Want to know more? {phone}"},
            {"step_number": 4, "delay_hours": 168, "delay_type": "days", "message_template": "Hi {name}, choosing the right surgeon for rhinoplasty is crucial. {doctor_name} at {clinic_name} has extensive experience in both cosmetic and functional rhinoplasty. Our approach focuses on natural, balanced results that complement your unique facial features. Would you like to see patient results? Reply 'yes'."},
            {"step_number": 5, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, if you've been researching rhinoplasty, you might have a lot of questions. That's completely normal. At {clinic_name}, the consultation is your safe space to discuss everything openly with {doctor_name}. No pressure, just expert guidance. Book your consultation: {booking_link}"},
            {"step_number": 6, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, just checking in from {clinic_name}. Many patients tell us that the hardest part was making the appointment, but once they met {doctor_name}, they felt completely at ease. We offer a thorough consultation where all your concerns are addressed. Ready when you are! {booking_link}"},
            {"step_number": 7, "delay_hours": 1440, "delay_type": "days", "message_template": "Hi {name}, hope you're doing well. A reminder that {clinic_name} offers financing options for rhinoplasty to make the procedure more accessible. {doctor_name} believes that feeling confident about your appearance shouldn't be limited by budget. Let us know if you'd like to discuss options. {phone}"},
            {"step_number": 8, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, we know rhinoplasty is a big decision and timing matters. Whenever you're ready, {doctor_name} and the team at {clinic_name} are here to help you every step of the way. Feel free to reach out with any questions, no matter how small. {booking_link}"},
            {"step_number": 9, "delay_hours": 3600, "delay_type": "days", "message_template": "Hi {name}, this is our final check-in from {clinic_name}. We've truly enjoyed connecting with you. Whenever the time feels right for rhinoplasty, remember that {doctor_name}'s expertise is just a call away. Wishing you all the best! {phone}"},
        ]
    },

    "facelift": {
        "name": "Facelift - 6 Month Nurture",
        "description": "Nurture sequence for facelift procedure leads",
        "procedure_category": "facelift",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for your interest in facelift at {clinic_name}. {doctor_name} specializes in natural-looking facial rejuvenation that turns back the clock without looking 'done.' Would you like to discuss what results are possible for you?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, modern facelift techniques have come a long way. {doctor_name} uses advanced methods that address sagging, jowls, and loose skin while maintaining your natural expressions. Recovery is typically 2-3 weeks, and results last 7-10 years. Want to know more? {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, at {clinic_name} we offer different levels of facial rejuvenation depending on your needs:\n\n- Mini facelift: Targets mild sagging, shorter recovery\n- Full facelift: Comprehensive rejuvenation\n- Neck lift: Can be combined for complete results\n\n{doctor_name} will recommend the best approach during consultation. {booking_link}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, a well-done facelift should make people say 'you look great' not 'you had work done.' That's exactly the philosophy {doctor_name} follows at {clinic_name}. Every procedure is customized to your facial anatomy. Ready for a consultation? {phone}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in from {clinic_name}. If you've been considering facial rejuvenation, non-surgical options like thread lifts are also available for those not ready for surgery. {doctor_name} can help you explore all options. Book a consultation: {booking_link}"},
            {"step_number": 6, "delay_hours": 1440, "delay_type": "days", "message_template": "Hi {name}, the best time for a facelift is when you first start noticing the signs. Catching it early means less invasive procedures and more natural results. {doctor_name} at {clinic_name} offers honest assessments. No upselling, just what's best for you. {booking_link}"},
            {"step_number": 7, "delay_hours": 2880, "delay_type": "days", "message_template": "Hi {name}, hope all is well. Just a reminder that {clinic_name} is here whenever you're ready. Facial rejuvenation is deeply personal, and we respect your timeline completely. {doctor_name}'s team is always available for questions. {phone}"},
        ]
    },

    "blepharoplasty": {
        "name": "Eyelid Surgery (Blepharoplasty) - 6 Month Nurture",
        "description": "Nurture sequence for eyelid surgery leads",
        "procedure_category": "blepharoplasty",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thanks for your interest in eyelid surgery at {clinic_name}. Blepharoplasty can address droopy eyelids, under-eye bags, and give you a refreshed, more youthful look. {doctor_name} would love to discuss your goals. Would you like to schedule a consultation? {booking_link}"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, eyelid surgery is one of the most transformative procedures with minimal downtime. Most patients at {clinic_name} return to normal activities within 7-10 days. The results are subtle yet dramatic, making you look rested and refreshed. Want to learn more? {phone}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, did you know that upper eyelid surgery can also improve your field of vision if droopy lids are blocking your sight? {doctor_name} evaluates both functional and cosmetic aspects during consultation. This means insurance may cover part of the procedure in some cases. Interested? {booking_link}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, the eyes are the first thing people notice. Eyelid surgery at {clinic_name} creates natural results that enhance your overall appearance. {doctor_name}'s precise technique ensures minimal scarring hidden within natural eyelid creases. Ready to explore your options? {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, check-in from {clinic_name}. Many patients combine upper and lower eyelid surgery for comprehensive rejuvenation. {doctor_name} can advise on the best approach for your specific needs. We also offer non-surgical alternatives like fillers for under-eye hollows. Let's discuss! {phone}"},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, hope you're well. Just a reminder from {clinic_name} that our team is here whenever you're ready. Eyelid surgery results last for many years, and patients consistently rate it as one of their best decisions. {doctor_name} looks forward to helping you. {booking_link}"},
        ]
    },

    "liposuction": {
        "name": "Liposuction - 6 Month Nurture",
        "description": "Nurture sequence for liposuction leads",
        "procedure_category": "liposuction",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for your interest in liposuction at {clinic_name}. We understand that stubborn fat can be frustrating even with diet and exercise. {doctor_name} specializes in body contouring that creates natural, proportionate results. Would you like to know more?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, modern liposuction at {clinic_name} isn't like what you might have seen years ago. {doctor_name} uses advanced techniques like VASER or power-assisted liposuction for more precise fat removal, faster recovery, and smoother results. Most patients return to light activity within a week. Interested in a consultation? {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, liposuction is most effective for areas that resist diet and exercise:\n\n- Abdomen and love handles\n- Thighs (inner and outer)\n- Arms\n- Chin and neck\n- Back\n\n{doctor_name} will assess your target areas and create a customized plan during consultation. {booking_link}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, one important thing to know: liposuction permanently removes fat cells from treated areas. This means that with a healthy lifestyle, your new contours are long-lasting. {doctor_name} at {clinic_name} focuses on creating results that look natural from every angle. Want to explore your options? {phone}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in from {clinic_name}. If you're considering body contouring, we also offer non-surgical options like CoolSculpting for smaller areas. {doctor_name} can help you decide which approach is best during a consultation. No pressure, just expert advice. {booking_link}"},
            {"step_number": 6, "delay_hours": 1440, "delay_type": "days", "message_template": "Hi {name}, many of our patients say that liposuction gave them the motivation to maintain a healthier lifestyle. It's not just about removing fat. It's about gaining confidence and feeling comfortable in your own body. {doctor_name} at {clinic_name} is here when you're ready. {booking_link}"},
            {"step_number": 7, "delay_hours": 2880, "delay_type": "days", "message_template": "Hi {name}, hope you're doing great. This is a friendly reminder from {clinic_name}. Whenever you decide to move forward with body contouring, {doctor_name}'s team is here to guide you through every step. No rush. Your timeline, your pace. {phone}"},
        ]
    },

    "breast_augmentation": {
        "name": "Breast Augmentation - 6 Month Nurture",
        "description": "Nurture sequence for breast augmentation leads",
        "procedure_category": "breast_augmentation",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for your interest in breast augmentation at {clinic_name}. This is a deeply personal decision, and {doctor_name} is committed to helping you achieve results that feel right for you. Would you like to schedule a private consultation?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, at {clinic_name}, {doctor_name} offers multiple options for breast augmentation including silicone implants, saline implants, and fat transfer. The consultation includes detailed sizing and 3D simulation so you can see potential results before making a decision. Interested? {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, here's what to expect at your consultation:\n\n- Detailed discussion of your goals\n- Physical assessment\n- Implant sizing with 3D simulation\n- Review of incision options\n- Recovery timeline\n- Transparent pricing\n\nNo pressure, just information to help you decide. {booking_link}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, choosing the right surgeon for breast augmentation is the most important decision. {doctor_name} prioritizes natural-looking results that complement your body proportions. Our patients consistently say they feel more confident without looking 'overdone.' Want to see results? {phone}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, check-in from {clinic_name}. If you have any concerns about safety or recovery, {doctor_name} uses the latest techniques for minimal scarring and faster healing. Most patients return to desk work within a week and full activity within 4-6 weeks. Questions? {booking_link}"},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, we understand that timing and privacy matter for this procedure. {clinic_name} ensures complete discretion throughout your journey. When you're ready, {doctor_name}'s team is here. Financing options are available too. {booking_link}"},
            {"step_number": 7, "delay_hours": 3600, "delay_type": "days", "message_template": "Hi {name}, final note from {clinic_name}. We've valued connecting with you. Whenever the time is right, remember that {doctor_name} is here to help you feel your absolute best. Wishing you well! {phone}"},
        ]
    },

    "tummy_tuck": {
        "name": "Tummy Tuck (Abdominoplasty) - 6 Month Nurture",
        "description": "Nurture sequence for tummy tuck leads",
        "procedure_category": "tummy_tuck",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thanks for reaching out about abdominoplasty at {clinic_name}. A tummy tuck can dramatically improve your abdominal contour, especially after pregnancy or significant weight loss. {doctor_name} would love to discuss your goals. {booking_link}"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, a tummy tuck at {clinic_name} addresses loose skin, separated muscles, and excess fat in the abdominal area. {doctor_name} tailors the procedure to your body. Options include mini tummy tuck for lower belly or full abdominoplasty for comprehensive contouring. Want to know which suits you? {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, many of our tummy tuck patients are post-pregnancy moms or people who've lost significant weight. They all share one thing: diet and exercise alone couldn't fix the loose skin. {doctor_name} specializes in restoring a flat, toned look. Ready to explore? {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, recovery from a tummy tuck typically involves 2-3 weeks of restricted activity. {doctor_name} at {clinic_name} uses techniques that minimize pain and speed up healing. Many patients say the recovery was easier than expected. Questions? {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month update from {clinic_name}. Some patients combine tummy tuck with liposuction for a complete body transformation. {doctor_name} calls this a 'mommy makeover' approach. If you're interested in comprehensive body contouring, let's discuss. {booking_link}"},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, we know body contouring surgery is a major decision. {clinic_name} is here whenever you're ready. {doctor_name} provides honest, no-pressure consultations to help you make an informed choice. Financing is available. {phone}"},
        ]
    },

    # =========================================================================
    # DERMATOLOGY / SKIN
    # =========================================================================

    "botox": {
        "name": "Botox - 6 Month Nurture",
        "description": "Nurture sequence for Botox treatment leads",
        "procedure_category": "botox",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for your interest in Botox at {clinic_name}! Botox is the world's most popular non-surgical cosmetic treatment, and {doctor_name} is highly experienced in delivering natural, refreshed results. Would you like to book a quick consultation?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, Botox at {clinic_name} takes just 15-20 minutes with no downtime. It effectively smooths:\n\n- Forehead lines\n- Frown lines (11s)\n- Crow's feet\n- Bunny lines\n\nResults show in 3-5 days and last 3-4 months. {doctor_name} focuses on a natural look. Interested? {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, worried about looking 'frozen'? At {clinic_name}, {doctor_name} uses a conservative approach. Our patients still express emotions naturally. They just look more refreshed and rested. It's the kind of treatment where people notice you look great but can't pinpoint why. Want to try? {booking_link}"},
            {"step_number": 4, "delay_hours": 168, "delay_type": "days", "message_template": "Hi {name}, fun fact: regular Botox treatments actually prevent new wrinkles from forming. Starting in your late 20s or 30s (preventive Botox) means you maintain smoother skin for longer. {doctor_name} at {clinic_name} can create a personalized plan. {phone}"},
            {"step_number": 5, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, if you've been hesitant about Botox, know that it's one of the safest cosmetic treatments with decades of proven results. At {clinic_name}, {doctor_name} uses premium, FDA-approved products. Your safety and satisfaction come first. Ready to try? {booking_link}"},
            {"step_number": 6, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in! Many of our patients combine Botox with fillers for comprehensive facial rejuvenation. Botox handles the lines, fillers restore volume. {doctor_name} can suggest the perfect combination during consultation. {booking_link}"},
            {"step_number": 7, "delay_hours": 1440, "delay_type": "days", "message_template": "Hi {name}, a lot of people try Botox for the first time and wonder why they waited so long. It's quick, effective, and the results speak for themselves. {clinic_name} is here whenever you're ready to take the plunge! {phone}"},
            {"step_number": 8, "delay_hours": 2880, "delay_type": "days", "message_template": "Hi {name}, hope you're doing well. Just a note from {clinic_name}. Botox is a great starting point for anyone new to cosmetic treatments. Low commitment, high impact. {doctor_name}'s team is here whenever you'd like to try it. {booking_link}"},
        ]
    },

    "fillers": {
        "name": "Dermal Fillers - 6 Month Nurture",
        "description": "Nurture sequence for filler treatment leads",
        "procedure_category": "fillers",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for your interest in dermal fillers at {clinic_name}. Whether it's lip enhancement, cheek contouring, or restoring volume, {doctor_name} creates beautiful, natural results. Would you like to discuss what fillers can do for you?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, dermal fillers at {clinic_name} can:\n\n- Plump and define lips\n- Restore cheek volume\n- Smooth nasolabial folds\n- Enhance jawline\n- Fill under-eye hollows\n- Non-surgical nose reshaping\n\nResults are instant and last 6-18 months. {doctor_name} uses premium hyaluronic acid fillers. Interested? {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, the best thing about fillers is they're reversible. If you don't love the result (which is rare!), it can be dissolved. This makes fillers the safest way to try facial enhancement. {doctor_name} at {clinic_name} focuses on subtle, enhancing results. Want to book? {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, a skilled injector makes all the difference with fillers. {doctor_name} has extensive training in facial anatomy and injection techniques. At {clinic_name}, we never overdo it. The goal is always natural enhancement. Ready to explore? {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, check-in from {clinic_name}. Filler treatments take just 30-45 minutes with minimal downtime. Most patients go right back to their day afterward. If you've been considering it, now is a great time. {booking_link}"},
            {"step_number": 6, "delay_hours": 1440, "delay_type": "days", "message_template": "Hi {name}, we understand that trying fillers for the first time can feel like a big step. At {clinic_name}, {doctor_name} always starts conservatively. You can always add more later. This approach ensures you're 100% happy. {phone}"},
            {"step_number": 7, "delay_hours": 2880, "delay_type": "days", "message_template": "Hi {name}, hope you're well. Fillers remain one of the most popular and satisfying cosmetic treatments. When you're ready to enhance your natural beauty, {doctor_name} at {clinic_name} is here. {booking_link}"},
        ]
    },

    "chemical_peel": {
        "name": "Chemical Peel - 6 Month Nurture",
        "description": "Nurture sequence for chemical peel leads",
        "procedure_category": "chemical_peel",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thanks for your interest in chemical peels at {clinic_name}. Chemical peels are excellent for treating pigmentation, acne scars, dull skin, and fine lines. {doctor_name} customizes the peel type and strength for your specific skin needs. Would you like a skin consultation?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, {clinic_name} offers multiple peel options:\n\n- Light peels: Gentle, no downtime, great for glow\n- Medium peels: Targets pigmentation and mild scarring\n- Deep peels: For significant skin concerns\n\n{doctor_name} will assess your skin and recommend the right type. Book your skin analysis: {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, chemical peels work by removing damaged outer layers of skin, revealing fresher, smoother skin underneath. A series of 4-6 sessions gives the best results. At {clinic_name}, we use medical-grade peels for superior outcomes. Interested? {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, many patients combine chemical peels with other treatments like microneedling or PRP for enhanced results. {doctor_name} at {clinic_name} creates customized treatment plans. If you're looking for overall skin rejuvenation, let's talk. {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in. If you're dealing with stubborn pigmentation or uneven skin tone, chemical peels are one of the most effective solutions. {doctor_name} at {clinic_name} has treated hundreds of similar cases. Ready to start your skin transformation? {booking_link}"},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, beautiful skin is a journey, not a destination. At {clinic_name}, {doctor_name}'s team is here to guide you through every step. When you're ready for glowing, healthy skin, book a consultation. {phone}"},
        ]
    },

    "microneedling": {
        "name": "Microneedling - 6 Month Nurture",
        "description": "Nurture sequence for microneedling treatment leads",
        "procedure_category": "microneedling",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thanks for your interest in microneedling at {clinic_name}. This treatment stimulates your skin's natural collagen production for smoother, firmer, more youthful skin. {doctor_name} uses advanced dermapen technology. Would you like to know more?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, microneedling at {clinic_name} is effective for:\n\n- Acne scars\n- Fine lines and wrinkles\n- Large pores\n- Uneven skin texture\n- Stretch marks\n- Dull skin\n\nMost patients see noticeable improvement after 3-4 sessions. {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, microneedling combined with PRP (Platelet-Rich Plasma) is the ultimate skin rejuvenation combo. Your body's own growth factors supercharge the healing process. {doctor_name} at {clinic_name} offers this premium combination. Interested? {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, what we love about microneedling is that it works for all skin types and tones. Unlike some laser treatments, there's minimal risk of hyperpigmentation. Sessions take about 45 minutes with just 1-2 days of mild redness. Ready to start? {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, check-in from {clinic_name}. Regular microneedling sessions (monthly for 4-6 months, then maintenance) can truly transform your skin. Our patients consistently report compliments on their skin quality. {doctor_name} would love to create your plan. {booking_link}"},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, clear, glowing skin boosts confidence like nothing else. At {clinic_name}, {doctor_name}'s microneedling results speak for themselves. Whenever you're ready, we're here to help you achieve your best skin. {phone}"},
        ]
    },

    "laser_hair_removal": {
        "name": "Laser Hair Removal - 6 Month Nurture",
        "description": "Nurture sequence for laser hair removal leads",
        "procedure_category": "laser_hair_removal",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for inquiring about laser hair removal at {clinic_name}. Say goodbye to waxing, shaving, and ingrown hairs! {doctor_name}'s team uses advanced laser technology for safe, effective permanent hair reduction. Which area are you considering?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, laser hair removal at {clinic_name}:\n\n- Works on face, underarms, bikini, legs, back, and more\n- 6-8 sessions for best results\n- Sessions are quick (underarms: 10 min, full legs: 45 min)\n- Our laser works on all skin tones\n\nBook your first session or a patch test: {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, did you know that the money spent on a lifetime of waxing far exceeds laser hair removal? Laser is a one-time investment for permanent smoothness. {clinic_name} offers affordable packages for multiple sessions. Want pricing details? {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, at {clinic_name} we use FDA-approved lasers that are safe for all skin types including Indian skin. {doctor_name}'s team ensures the settings are customized for your skin tone and hair type. Safety first, always. Ready to start? {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in. Many of our patients start with one area and then extend to others once they see the amazing results. It's that satisfying! If you'd like to start with a small area, we can do that. {booking_link}"},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, imagine never having to worry about unwanted hair again. That's what laser hair removal offers. {clinic_name} has helped hundreds of patients achieve smooth, carefree skin. {doctor_name}'s team is ready when you are. {phone}"},
        ]
    },

    "acne_treatment": {
        "name": "Acne Treatment - 6 Month Nurture",
        "description": "Nurture sequence for acne treatment leads",
        "procedure_category": "acne_treatment",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thanks for reaching out to {clinic_name} about acne treatment. We understand how frustrating acne can be. {doctor_name} takes a comprehensive approach to identify the root cause and create an effective treatment plan. Would you like to schedule a skin assessment?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, at {clinic_name}, {doctor_name} treats acne using a combination approach:\n\n- Medical-grade topical treatments\n- Oral medications when needed\n- Chemical peels for active acne\n- LED light therapy\n- Lifestyle and diet guidance\n\nThe right combination depends on your acne type and severity. Book your assessment: {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, most acne can be significantly improved within 8-12 weeks with the right treatment. The key is consistency and the right products for YOUR skin. Generic products often make acne worse. {doctor_name} at {clinic_name} prescribes targeted treatments. Interested? {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, dealing with acne affects more than just skin. It affects confidence. At {clinic_name}, we treat the whole picture. {doctor_name} addresses active acne and then works on scarring and pigmentation. A complete plan for clear, confident skin. {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, check-in from {clinic_name}. If you've tried over-the-counter products without success, it's time for professional help. Dermatologist-led treatment is more effective and often costs less in the long run than buying products that don't work. {booking_link}"},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, clear skin is achievable with the right guidance. {doctor_name} at {clinic_name} has helped hundreds of patients overcome acne. When you're ready, we're here. {phone}"},
        ]
    },

    "pigmentation_treatment": {
        "name": "Pigmentation Treatment - 6 Month Nurture",
        "description": "Nurture sequence for pigmentation/melasma leads",
        "procedure_category": "pigmentation_treatment",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for your interest in pigmentation treatment at {clinic_name}. Dark spots, melasma, and uneven skin tone are among the most common skin concerns, and {doctor_name} has extensive experience treating them. Would you like a consultation?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, pigmentation treatment at {clinic_name} involves a customized approach:\n\n- Medical-grade lightening creams\n- Chemical peels targeted for pigmentation\n- Laser treatments for stubborn spots\n- PRP for overall skin rejuvenation\n- Sun protection guidance\n\n{doctor_name} first identifies the type and depth of pigmentation. {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, important to know: pigmentation treatment requires patience and consistency. Results typically show in 6-12 weeks. {doctor_name} at {clinic_name} creates realistic timelines and tracks progress at every visit. Ready to start your journey to even-toned skin? {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, one common mistake with pigmentation is using random products that can actually worsen the condition. Professional assessment ensures you're using the right ingredients for your specific type of pigmentation. {doctor_name} at {clinic_name} can guide you. {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in from {clinic_name}. If pigmentation has been bothering you, professional treatment combined with the right home care routine can make a dramatic difference. {doctor_name} provides a complete protocol. Let's get started! {booking_link}"},
            {"step_number": 6, "delay_hours": 2880, "delay_type": "days", "message_template": "Hi {name}, even-toned, glowing skin is absolutely achievable. {clinic_name} has helped many patients overcome stubborn pigmentation. {doctor_name}'s expert care and proven protocols deliver results. We're here when you're ready. {phone}"},
        ]
    },

    "hydrafacial": {
        "name": "HydraFacial - 6 Month Nurture",
        "description": "Nurture sequence for HydraFacial leads",
        "procedure_category": "hydrafacial",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thanks for your interest in HydraFacial at {clinic_name}! It's the ultimate skin rejuvenation treatment that cleanses, exfoliates, extracts, and hydrates all in one session. Results are instant with zero downtime. Would you like to book? {booking_link}"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, HydraFacial at {clinic_name} is perfect for:\n\n- Dull, tired skin\n- Clogged pores and blackheads\n- Fine lines\n- Uneven skin texture\n- Pre-event glow\n\nTreatment takes 30-45 minutes and you leave glowing. No redness, no peeling. {doctor_name} customizes each session. {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, while a single HydraFacial gives amazing results, monthly sessions provide cumulative benefits. Think of it as a deep-clean and vitamin boost for your skin every month. {clinic_name} offers packages for regular sessions. Interested? {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, HydraFacial is loved by celebrities and skin experts worldwide for a reason. It's effective for ALL skin types with zero side effects. At {clinic_name}, we use genuine HydraFacial technology with premium serums. Your skin deserves the best! {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in. If you have an upcoming event, wedding, or just want to look your best, a HydraFacial 3-5 days before is the perfect prep. {clinic_name} is here for you. Book: {booking_link}"},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, great skin starts with great care. {clinic_name}'s HydraFacial delivers consistent, visible results every time. {doctor_name}'s team is here whenever you want to treat yourself. {phone}"},
        ]
    },

    "anti_aging": {
        "name": "Anti-Aging Treatment - 6 Month Nurture",
        "description": "General anti-aging treatment nurture sequence",
        "procedure_category": "anti_aging",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for your interest in anti-aging treatments at {clinic_name}. {doctor_name} offers a range of solutions from non-invasive treatments to advanced procedures. The first step is understanding your specific concerns. Would you like to schedule a consultation? {booking_link}"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, at {clinic_name}, our anti-aging approach includes:\n\n- Botox for lines and wrinkles\n- Fillers for volume restoration\n- Laser skin resurfacing\n- Microneedling with PRP\n- Medical-grade skincare\n- Thread lifts for non-surgical tightening\n\n{doctor_name} creates personalized plans based on your goals and budget. {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, the best anti-aging strategy is proactive, not reactive. Starting treatments early preserves your youthful appearance rather than trying to reverse years of damage later. {doctor_name} at {clinic_name} can create an age-appropriate plan. Interested? {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, modern anti-aging treatments are subtle and natural. Nobody should be able to tell you've had work done. You just look refreshed, rested, and vibrant. That's the {clinic_name} approach. {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in from {clinic_name}. Many of our patients start with one treatment and gradually build their routine. There's no rush. {doctor_name} guides you at your comfort level. Ready to explore? {booking_link}"},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, aging gracefully is about feeling confident at every stage. {clinic_name} is here to support your skin health journey. {doctor_name}'s expertise ensures safe, effective results. We're here whenever you're ready. {phone}"},
        ]
    },

    "tattoo_removal": {
        "name": "Tattoo Removal - 6 Month Nurture",
        "description": "Nurture sequence for laser tattoo removal leads",
        "procedure_category": "tattoo_removal",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thanks for reaching out about tattoo removal at {clinic_name}. Whether you want complete removal or fading for a cover-up, {doctor_name}'s advanced laser technology can help. Would you like a free assessment?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, tattoo removal at {clinic_name}:\n\n- Uses advanced Q-switched/PicoSure laser\n- Works on all ink colors\n- Sessions spaced 6-8 weeks apart\n- 6-12 sessions for full removal typically\n- Minimal scarring risk\n\n{doctor_name} can assess your tattoo and give you a realistic timeline. {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, the number of sessions needed depends on your tattoo's size, color, age, and ink depth. During consultation, {doctor_name} will evaluate all factors and give you an honest timeline and cost estimate. No surprises. {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, if you're planning a cover-up tattoo, laser fading first gives your tattoo artist a much better canvas to work with. Even 3-4 sessions can make a huge difference. {clinic_name} works with many clients preparing for cover-ups. Interested? {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, check-in from {clinic_name}. If the cost of full treatment is a concern, we offer per-session pricing and packages. {doctor_name} also offers payment plans to make it manageable. Everyone deserves a fresh start. {booking_link}"},
            {"step_number": 6, "delay_hours": 2880, "delay_type": "days", "message_template": "Hi {name}, a tattoo doesn't have to be forever if you don't want it to be. {clinic_name}'s laser removal technology continues to advance, making removal faster and more effective. {doctor_name}'s team is here when you're ready. {phone}"},
        ]
    },

    "scar_treatment": {
        "name": "Scar Treatment - 6 Month Nurture",
        "description": "Nurture sequence for scar treatment leads",
        "procedure_category": "scar_treatment",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for your interest in scar treatment at {clinic_name}. Whether it's acne scars, surgical scars, or injury scars, {doctor_name} has effective solutions to improve their appearance. Would you like a consultation?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, {clinic_name} offers multiple scar treatment options:\n\n- Microneedling for acne scars\n- Laser resurfacing\n- Chemical peels\n- PRP therapy\n- Subcision for deep scars\n- Filler injections for depressed scars\n\n{doctor_name} will assess your scars and recommend the best approach. {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, scar treatment usually requires a series of sessions for best results. The good news is that modern techniques can significantly improve even old, stubborn scars. {doctor_name} at {clinic_name} has seen remarkable transformations. Want to discuss your case? {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, many patients combine scar treatment with overall skin rejuvenation for comprehensive results. {doctor_name} at {clinic_name} creates holistic plans that address scars while improving overall skin quality. Interested? {booking_link}"},
            {"step_number": 5, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, scars may tell a story, but you don't have to live with them forever. {clinic_name}'s advanced treatments can significantly reduce their visibility. {doctor_name} is here to help whenever you're ready. {phone}"},
        ]
    },

    # =========================================================================
    # BODY CONTOURING (NON-SURGICAL)
    # =========================================================================

    "coolsculpting": {
        "name": "CoolSculpting - 6 Month Nurture",
        "description": "Nurture sequence for CoolSculpting body contouring leads",
        "procedure_category": "coolsculpting",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thanks for your interest in CoolSculpting at {clinic_name}! This FDA-cleared treatment freezes and eliminates stubborn fat without surgery. {doctor_name}'s team would love to assess if CoolSculpting is right for you. {booking_link}"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, CoolSculpting at {clinic_name}:\n\n- Non-surgical fat reduction\n- No needles, no anesthesia, no downtime\n- Treats belly, love handles, thighs, arms, chin\n- 20-25% fat reduction per session\n- Results visible in 2-3 months\n\nIt's literally a 'lunch break' procedure. Interested? {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, CoolSculpting works by freezing fat cells which your body then naturally eliminates. Once those fat cells are gone, they're gone for good. {doctor_name} at {clinic_name} creates a treatment plan targeting your specific problem areas. Want to know more? {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, the best CoolSculpting candidates are close to their ideal weight but have stubborn pockets of fat that won't budge. If that sounds like you, {clinic_name} can help. {doctor_name} will assess and tell you honestly if CoolSculpting is the right option. {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in. Many patients combine CoolSculpting with a healthy lifestyle for optimal results. At {clinic_name}, we support your whole body transformation journey, not just the procedure. Ready? {booking_link}"},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, stubborn fat doesn't have to be permanent. CoolSculpting at {clinic_name} offers a safe, effective solution. {doctor_name}'s team is here whenever you're ready to sculpt your ideal shape. {phone}"},
        ]
    },

    "skin_tightening": {
        "name": "Skin Tightening - 6 Month Nurture",
        "description": "Nurture sequence for non-surgical skin tightening leads",
        "procedure_category": "skin_tightening",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thanks for your interest in skin tightening at {clinic_name}. We offer non-surgical solutions using radiofrequency and ultrasound technology to tighten and firm loose skin. {doctor_name} can assess the best approach for you. {booking_link}"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, non-surgical skin tightening at {clinic_name} works by stimulating collagen production deep in the skin. Over 2-3 months, skin naturally firms and tightens. Great for face, neck, arms, and abdomen. No surgery, no downtime. Interested? {phone}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, most patients need 3-6 sessions for optimal skin tightening results. It's a gradual improvement that looks completely natural. {doctor_name} at {clinic_name} uses the latest devices for consistent results. Want to start? {booking_link}"},
            {"step_number": 4, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in from {clinic_name}. If you're noticing skin laxity on your face or body, non-surgical skin tightening is an excellent first step before considering surgery. {doctor_name} can evaluate your options. {booking_link}"},
            {"step_number": 5, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, firm, tight skin is achievable without going under the knife. {clinic_name}'s advanced skin tightening treatments deliver noticeable results. {doctor_name} is here when you're ready. {phone}"},
        ]
    },

    # =========================================================================
    # DENTAL AESTHETICS
    # =========================================================================

    "smile_makeover": {
        "name": "Smile Makeover - 6 Month Nurture",
        "description": "Nurture sequence for dental veneers/smile makeover leads",
        "procedure_category": "smile_makeover",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for your interest in a smile makeover at {clinic_name}. A beautiful smile can transform your entire appearance and boost confidence. {doctor_name} specializes in creating natural, stunning smiles. Would you like a consultation? {booking_link}"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, a smile makeover at {clinic_name} can include:\n\n- Porcelain veneers for a Hollywood smile\n- Teeth whitening for a brighter smile\n- Dental bonding for chips and gaps\n- Gum contouring for a balanced smile\n\n{doctor_name} designs each smile to complement your face. Interested? {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, veneers are the gold standard for smile transformations. At {clinic_name}, {doctor_name} uses ultra-thin porcelain veneers that look completely natural. The process typically takes 2-3 visits. Results last 10-15 years with proper care. {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, a smile makeover is one of the most life-changing cosmetic investments you can make. Our patients consistently tell us how their confidence soared after the procedure. {doctor_name} at {clinic_name} would love to help you smile freely. {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, check-in from {clinic_name}. If cost is a concern, we offer flexible payment plans for smile makeover treatments. {doctor_name} believes everyone deserves to love their smile. Let's discuss your options. {phone}"},
            {"step_number": 6, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, your perfect smile is waiting. {clinic_name}'s smile makeover results speak for themselves. {doctor_name} is here whenever you're ready to transform your smile. {booking_link}"},
        ]
    },

    "teeth_whitening": {
        "name": "Teeth Whitening - 6 Month Nurture",
        "description": "Nurture sequence for teeth whitening leads",
        "procedure_category": "teeth_whitening",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thanks for your interest in teeth whitening at {clinic_name}! Professional whitening can brighten your smile by several shades in just one session. {doctor_name}'s team uses safe, effective methods. Would you like to book? {booking_link}"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, professional teeth whitening at {clinic_name} is far more effective than over-the-counter products. Our in-office treatment takes about 60 minutes and can lighten teeth by 4-8 shades. Safe, fast, and supervised by {doctor_name}. Interested? {phone}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, if you have a wedding, party, interview, or just want to feel more confident, teeth whitening is the quickest aesthetic upgrade. One session at {clinic_name} and you'll see an immediate difference. Book now: {booking_link}"},
            {"step_number": 4, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, check-in from {clinic_name}. A bright smile is just one appointment away. Professional whitening results last 6-12 months with proper care. {doctor_name}'s team also provides at-home maintenance kits. Ready to brighten your smile? {booking_link}"},
            {"step_number": 5, "delay_hours": 2160, "delay_type": "days", "message_template": "Hi {name}, your smile is your signature. {clinic_name}'s teeth whitening gives you a confidence boost that everyone notices. {doctor_name} is here when you're ready. {phone}"},
        ]
    },

    # =========================================================================
    # GENERAL / CONSULTATION
    # =========================================================================

    "general_consultation": {
        "name": "General Consultation - 6 Month Nurture",
        "description": "Generic nurture for leads who didn't specify a procedure",
        "procedure_category": "general",
        "steps": [
            {"step_number": 1, "delay_hours": 0, "delay_type": "hours", "message_template": "Hi {name}, thank you for reaching out to {clinic_name}! We offer a wide range of aesthetic and medical treatments. {doctor_name}'s team is here to help you look and feel your best. What specific concern can we help you with?"},
            {"step_number": 2, "delay_hours": 24, "delay_type": "days", "message_template": "Hi {name}, whether you're interested in skin treatments, hair restoration, body contouring, or cosmetic procedures, {clinic_name} has expert solutions. {doctor_name} provides personalized consultations to understand your goals. Book yours: {booking_link}"},
            {"step_number": 3, "delay_hours": 72, "delay_type": "days", "message_template": "Hi {name}, at {clinic_name} we believe every treatment journey starts with understanding your unique needs. {doctor_name} takes time to listen, assess, and recommend the best approach. No pressure, no upselling. Just honest, expert guidance. {phone}"},
            {"step_number": 4, "delay_hours": 336, "delay_type": "days", "message_template": "Hi {name}, just checking in from {clinic_name}. If you're still exploring your options, we're happy to answer any questions. Sometimes a consultation with {doctor_name} helps clarify what's possible and what's right for you. It's free and there's no obligation. {booking_link}"},
            {"step_number": 5, "delay_hours": 720, "delay_type": "days", "message_template": "Hi {name}, one month check-in from {clinic_name}. We hope you're doing well! Whether it's today or months from now, {doctor_name}'s team is here whenever you're ready to explore your aesthetic goals. Feel free to reach out anytime. {phone}"},
            {"step_number": 6, "delay_hours": 1440, "delay_type": "days", "message_template": "Hi {name}, hope all is well. {clinic_name} regularly introduces new treatments and technology. If you'd like to stay updated on our latest offerings and special packages, just reply 'yes' and we'll keep you informed. {doctor_name}'s team sends our best! {booking_link}"},
            {"step_number": 7, "delay_hours": 2880, "delay_type": "days", "message_template": "Hi {name}, final note from {clinic_name}. We've truly appreciated the opportunity to connect with you. Whenever you're ready to enhance your appearance or address any concern, {doctor_name} and the team are just a message away. Wishing you all the best! {phone}"},
        ]
    },
}


def get_all_template_categories() -> list:
    """Return a list of all available template categories."""
    return [
        {"key": key, "name": template["name"], "category": template["procedure_category"]}
        for key, template in NURTURE_TEMPLATES.items()
    ]


def get_template(template_key: str) -> dict:
    """Get a specific template by its key."""
    return NURTURE_TEMPLATES.get(template_key)


def get_templates_by_category(category: str) -> list:
    """Get all templates matching a procedure category."""
    return [
        {"key": key, **template}
        for key, template in NURTURE_TEMPLATES.items()
        if template["procedure_category"] == category
    ]
