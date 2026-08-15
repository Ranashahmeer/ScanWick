import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Link } from "@tanstack/react-router"

function CardLayout ({title, desc, inputFields, buttonText, footerDesc, link, linkPath, onFooterLinkClick, alertMessage, form, onSubmit} : any) {
    return (
        <div className="h-screen flex flex-col justify-center items-center gap-[24px]">
            <div className="w-sm sm:max-w-md flex flex-col gap-[8px]">
                {alertMessage}
            </div>
            
            <Card className="w-[482px] h-[346px] flex flex-col gap-[24px]">
                <CardHeader className="flex flex-col gap-2 items-center">
                    <CardTitle>{title}</CardTitle>
                    <CardDescription className="w-[290px] text-center text-base">{desc}</CardDescription>
                </CardHeader>

                <form onSubmit={form.handleSubmit(onSubmit)}>
                <CardContent className="px-[72px]">
                {inputFields}
                </CardContent>
                
                <CardFooter className="flex flex-col gap-[16px] items-center">
                    <Button className="w-[264px] rounded-[5px] bg-primary text-primary-foreground shadow-[0_8px_20px_rgba(0,34,15,0.18)] transition-transform hover:-translate-y-0.5 hover:bg-primary/90">{buttonText}</Button>
                    {footerDesc && (
                      <p className="mx-4 text-s text-slate-500">
                        {footerDesc}{" "}
                        {onFooterLinkClick ? (
                          <button type="button" className="text-[#1b7a4b] underline hover:text-[#00361c]" onClick={onFooterLinkClick}>{link}</button>
                        ) : (
                          <Link className="text-[#1b7a4b] underline hover:text-[#00361c]" to={linkPath}>{link}</Link>
                        )}
                      </p>
                    )}
                </CardFooter>
                </form>
            </Card> 
        </div>
    )
}

export default CardLayout