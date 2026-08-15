import { CardTitle, CardHeader, CardFooter, CardDescription } from "@/components/ui/card"
import { Field } from "@/components/ui/field";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Link } from "@tanstack/react-router";
import GoogleButton from "@/components/GoogleButton";
import Logo from '../assets/Logos/Full Scanwick Logo Dark Green.svg';
import { env } from "@/lib/env";

const AuthHeader = ({title, desc} : any) => {
  return (
    <CardHeader className="flex flex-col gap-2 items-center">
        <div>
        <img src={Logo} alt='Scanwick logo' width={150} />
        </div>
        <CardTitle>{title}</CardTitle>
        <CardDescription>
        {desc}
        </CardDescription>
    </CardHeader>
  )
}

const AuthFooter = ({buttonText, separatorText, desc, link, linkPath, submitting} : any) => {

    function handleGoogleClick() {
      window.location.href = `${env.authApiBaseUrl}/api/auth/google`
    }

    return (
        <CardFooter className="flex flex-col gap-[16px]">
            <Field orientation="horizontal" className="grid place-content-center">
            <Button
              variant="default"
              type="submit"
              disabled={submitting}
              className="w-[264px] rounded-[5px] bg-primary text-primary-foreground shadow-[0_8px_20px_rgba(0,34,15,0.18)] transition-transform hover:-translate-y-0.5 hover:bg-primary/90"
            >
                {buttonText}
            </Button>
            </Field>
            <div className="relative flex items-center w-full">
            <Separator className="flex-grow h-[1px] bg-slate-200" />

            <span className="mx-4 text-xs text-slate-500 shrink-0">{separatorText}</span>

            <Separator className="flex-grow h-[1px] bg-slate-200" />
            </div>
            <GoogleButton
            handleClick={handleGoogleClick}
            />
            <p className="mx-4 text-s text-slate-500">{desc} <Link className="text-[#1b7a4b] underline hover:text-[#00361c]" to={linkPath}>{link}</Link></p>
        </CardFooter>
    )
}

export {AuthHeader, AuthFooter}