import NavLink from "@/components/NavLink"

// Every footer link used to hardcode path='/' regardless of its label, so
// "Terms of Service", "Contact Us", etc. all silently navigated to the
// homepage instead of their real pages. Only map labels that have an actual
// route today (verified against routeTree.gen.ts) — everything else (e.g.
// "Careers", "Features", "Solutions", "Platforms", "Success Stories", "FAQ")
// has no page to link to yet, so it's rendered as plain, non-interactive
// text instead of a link that would silently go nowhere useful.
const ROUTE_BY_LABEL: Record<string, string> = {
  "About Us": "/about",
  Blog: "/blog",
  "Privacy Policy": "/privacy",
  "Terms of Service": "/terms",
  "Contact Us": "/contact",
}

const LinksList = ({heading, list} : {heading:string, list:Array<String>}) => {
  return (
    <ul>
        <li><strong>{heading}</strong></li>
        {list.map(listItem=>{
            const path = ROUTE_BY_LABEL[listItem as string]
            return (
                <li key={listItem as string}>
                    {path ? <NavLink path={path} name={listItem}/> : <span>{listItem}</span>}
                </li>
            )
        })}
    </ul>
  )
}

export default LinksList