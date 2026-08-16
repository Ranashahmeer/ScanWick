import { CardTitle, CardHeader, CardFooter, CardDescription } from "@/components/ui/card"
import { Field } from "@/components/ui/field";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Link } from "@tanstack/react-router";
import GoogleButton from "@/components/GoogleButton";
import Logo from '../assets/Logos/Full Scanwick Logo Dark Green.svg';
import { env } from "@/lib/env";

const AuthHeader = ({ title, desc }: { title: string; desc?: string }) => {
  return (
    <CardHeader className="flex flex-col gap-2 items-center text-center pb-2">
      <Link to="/" className="mb-2 transition-transform hover:scale-105">
        <img src={Logo} alt="Scanwick logo" width={140} />
      </Link>
      <CardTitle className="text-xl font-bold tracking-tight text-[#0E1512]">{title}</CardTitle>
      {desc ? (
        <CardDescription className="text-xs text-[#6B7A72]">
          {desc}
        </CardDescription>
      ) : null}
    </CardHeader>
  );
};

const AuthFooter = ({
  buttonText,
  separatorText,
  desc,
  link,
  linkPath,
  submitting,
}: {
  buttonText: string;
  separatorText?: string;
  desc?: string;
  link?: string;
  linkPath?: string;
  submitting?: boolean;
}) => {
  function handleGoogleClick() {
    window.location.href = `${env.authApiBaseUrl}/api/auth/google`;
  }

  return (
    <CardFooter className="flex flex-col gap-4 pt-2">
      <Field orientation="horizontal" className="w-full">
        <Button
          variant="default"
          type="submit"
          disabled={submitting}
          className="w-full h-11 rounded-lg bg-[#00361C] hover:bg-[#00220F] text-white font-semibold text-sm shadow-[0_4px_14px_rgba(0,34,15,0.15)] transition-all hover:-translate-y-0.5 disabled:opacity-50"
        >
          {submitting ? "Please wait..." : buttonText}
        </Button>
      </Field>

      {separatorText ? (
        <div className="relative flex items-center w-full my-1">
          <Separator className="flex-grow h-[1px] bg-[#DCE3DF]" />
          <span className="mx-3 text-[11px] font-medium text-[#6B7A72] uppercase tracking-wider shrink-0">
            {separatorText}
          </span>
          <Separator className="flex-grow h-[1px] bg-[#DCE3DF]" />
        </div>
      ) : null}

      {separatorText ? (
        <GoogleButton handleClick={handleGoogleClick} />
      ) : null}

      {desc && link && linkPath ? (
        <p className="text-xs text-center text-[#6B7A72] mt-1">
          {desc}{" "}
          <Link
            className="text-[#1B7A4B] font-semibold hover:text-[#00361C] hover:underline"
            to={linkPath}
          >
            {link}
          </Link>
        </p>
      ) : null}
    </CardFooter>
  );
};

export { AuthHeader, AuthFooter };