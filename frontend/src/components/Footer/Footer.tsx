import { Button } from "@/components/ui/button"
import {Card, CardContent} from '@/components/ui/card'
import linkedinIcon from '../../assets/linkedinIcon.svg'
import instaIcon from '../../assets/instaIcon.svg'
import xIcon from '../../assets/xIcon.svg'

import LinksList from "./LinksList"

const Footer = () => {
  return (
    <footer>

        <div className='grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 grid-rows-auto lg:grid-rows-2 divide-x divide-y divide-neutral'>

            <div className="py-[16px] md:py-[24px] pl-[16px] md:pl-[52px]">
                <Card size="sm" className="m-[8px] md:w-[248px] lg:w-[242px] py-[24px] px-[20px] md:px-[16px] border-[0.5px] border-neutral rounded-[10px] shadow-[0_0_30px_16px_rgba(0,0,0,0.1)] bg-gradient-to-b from-[#00361C] to-[#00220F]">
                    <CardContent className="flex flex-col gap-[16px]">
                        <p className='text-[14px] lg:text-[16px]/[24px] text-white'>
                            Upload a CSV file and turn raw data into valuable insights in just three steps.  No cards required to start.
                        </p>
                        <Button className='bg-white text-primary-purple border-[0.5px] border-neutral w-[108px] h-[36px] text-[12px]'>Get Started</Button>
                    </CardContent>
                </Card>
            </div>

            <div className="flex justify-center items-center py-[16px] md:py-[24px]">
                <LinksList heading="Company" list={['About Us', 'Careers', 'Blog']} />
            </div>

            <div className="flex justify-center items-center py-[16px] md:py-[24px]">
                <LinksList heading="Product" list={['Features', 'Solutions', 'Platforms']} />
            </div>
            
            <div className="md:order-0 order-[1] py-[16px] md:py-[24px] pl-[16px] md:pl-[52px] border-b-0">
                <div className='flex gap-[8px]'>
                    <a href='linkedin.com'><img src={linkedinIcon} alt="LinkedIn" /></a>
                    <a href='instagram.com'><img src={instaIcon} alt="Insta" /></a>
                    <a href="x.com"><img src={xIcon} alt="X" /></a>
                </div>
            </div>

            <div className="flex justify-center items-center border-b-0 py-[16px] md:py-[24px]">
                <LinksList heading="Resources" list={['Success Stories', 'FAQ']} />
            </div>

            <div className="flex justify-center items-center py-[16px] md:py-[24px]">
                <LinksList heading="Legal" list={['Privacy Policy', 'Terms of Service', 'Contact Us']} />
            </div>
        </div>

        <div className='px-[16px] md:px-[40px] py-[16px] md:py-[20px]'>
            <p className='text-[12px] md:text-[14px]'>&copy; 2026 Scanwick Ltd. All Right Reserved.</p>
        </div>

    </footer>

  )
}

export default Footer