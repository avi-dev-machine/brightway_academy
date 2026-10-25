import { PublicHeader } from "@/components/layout/public-header";
import { PublicFooter } from "@/components/layout/public-footer";
import { Card, CardContent } from "@/components/ui/card";
import { MapPin, Phone, Mail, Clock, HelpCircle } from "lucide-react";

export default function ContactPage() {
  const academyName =
    process.env.NEXT_PUBLIC_ACADEMY_NAME || "Brightway Computer Academy";
  const academyAddress = process.env.NEXT_PUBLIC_ACADEMY_ADDRESS;
  const academyPhone = process.env.NEXT_PUBLIC_ACADEMY_PHONE;
  const academyEmail = process.env.NEXT_PUBLIC_ACADEMY_EMAIL;
  const academyHours = process.env.NEXT_PUBLIC_ACADEMY_HOURS;
  const mapEmbedUrl = process.env.NEXT_PUBLIC_ACADEMY_MAP_EMBED_URL;

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <PublicHeader />

      <main className="flex-1 py-12">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
              Contact & Support Desk
            </h1>
            <p className="mt-3 text-sm text-slate-600">
              Reach out to our campus office for admission counseling, student support, or general enquiries.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
            <div className="space-y-6">
              <Card>
                <CardContent className="p-6 space-y-4">
                  <h3 className="text-base font-bold text-slate-900">Academy Office Details</h3>

                  <div className="flex items-start gap-3">
                    <MapPin className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-semibold text-slate-900">Campus Address</p>
                      <p className="text-xs text-slate-600 mt-0.5">
                        {academyAddress || "Address details available via academy administration."}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Phone className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-semibold text-slate-900">Telephone / WhatsApp</p>
                      <p className="text-xs text-slate-600 mt-0.5">
                        {academyPhone || "Contact number available via academy administration."}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Mail className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-semibold text-slate-900">Official Email</p>
                      <p className="text-xs text-slate-600 mt-0.5">
                        {academyEmail || "office@brightwayacademy.com"}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Clock className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-semibold text-slate-900">Visiting Hours</p>
                      <p className="text-xs text-slate-600 mt-0.5">
                        {academyHours || "Monday – Saturday: 9:00 AM – 7:00 PM"}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-blue-50 border-blue-200">
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 text-blue-800 font-semibold text-sm">
                    <HelpCircle className="h-4 w-4" />
                    Enrolled Students Support
                  </div>
                  <p className="mt-2 text-xs text-blue-700 leading-relaxed">
                    Existing students can view payment histories, generate receipt PDFs, and track class attendance directly via the Student Portal.
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Map */}
            <div className="h-96 w-full rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden flex items-center justify-center">
              {mapEmbedUrl ? (
                <iframe
                  src={mapEmbedUrl}
                  width="100%"
                  height="100%"
                  style={{ border: 0 }}
                  allowFullScreen
                  loading="lazy"
                  title="Academy Location Map"
                />
              ) : (
                <div className="text-center p-6 text-slate-400">
                  <MapPin className="h-8 w-8 mx-auto mb-2 text-slate-400" />
                  <p className="text-xs font-medium text-slate-700">Campus Location</p>
                  <p className="text-[11px] text-slate-400 mt-1 max-w-xs">
                    {academyAddress || "Map embed will appear once the location URL is configured in academy settings."}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
